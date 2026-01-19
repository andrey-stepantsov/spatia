import os
import sqlite3
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from backend.main import app, DB_PATH, run_witness_process, watch_sentinel_db, lifespan
import backend.main
import backend.projector
import importlib.util
import sys

# Setup Test Client
client = TestClient(app)
TEST_DB = "test_coverage.db"

# --- Fixtures ---

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup global DB_PATH override for backend.main
    original_db_path = backend.main.DB_PATH
    backend.main.DB_PATH = TEST_DB
    
    # Clean setup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    # Basic schema (Added type and domain for shatter compatibility)
    cursor.execute("CREATE TABLE atoms (id TEXT PRIMARY KEY, status INTEGER, content TEXT, hash TEXT, last_witnessed TEXT, type TEXT, domain TEXT)")
    cursor.execute("CREATE TABLE geometry (atom_id TEXT PRIMARY KEY, x INTEGER, y INTEGER)")
    cursor.execute("INSERT INTO atoms (id, status, content, hash, last_witnessed, type, domain) VALUES ('existing_atom', 1, 'content', 'hash', 'ts', 'file', 'generic')")
    conn.commit()
    conn.close()
    
    # Logs dir
    os.makedirs(".spatia/logs", exist_ok=True)
    with open(".spatia/logs/existing_atom.log", "w") as f:
        f.write("Log content")
    
    yield
    
    # Teardown
    backend.main.DB_PATH = original_db_path
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except OSError:
            pass
    if os.path.exists(".spatia/logs/existing_atom.log"):
        os.remove(".spatia/logs/existing_atom.log")

# --- Existing Tests (Preserved/Updated) ---

def test_get_logs_success():
    response = client.get("/api/atoms/existing_atom/logs")
    assert response.status_code == 200
    assert response.json()["logs"] == "Log content"

def test_get_logs_not_found():
    response = client.get("/api/atoms/non_existent_atom/logs")
    assert response.status_code == 404

def test_witness_404():
    response = client.post("/api/witness", json={"atom_id": "ghost_atom"})
    # Expect 404 because ghost_atom is not in DB (setup_teardown inserts 'existing_atom')
    assert response.status_code == 404
    # Check detail - adapting to observed schema in other tests
    data = response.json()
    if 'detail' in data:
        assert "Atom not found" in data['detail']
    else:
        # Fallback to observed schema
        assert "Atom not found" in data['error']['message']

@patch('backend.main.manager.broadcast', new_callable=AsyncMock)
def test_witness_broadcasts_event(mock_broadcast):
    response = client.post("/api/witness", json={"atom_id": "existing_atom"})
    assert response.status_code == 200
    assert mock_broadcast.call_count >= 1

# --- New Coverage Tests ---

# 1. Background Loops: watch_sentinel_db
@pytest.mark.asyncio
async def test_watch_sentinel_db_flow():
    # Mock awatch to yield one event then stop (or we break manually)
    # We can mock it to return an AsyncIterator
    
    ms = MagicMock()
    ms.__aiter__.return_value = [[('modified', TEST_DB)]]
    
    with patch('backend.main.awatch', return_value=ms):
        with patch('backend.main.manager.broadcast', new_callable=AsyncMock) as mock_broadcast:
            # We need to run watch_sentinel_db but interrupt it or let it finish if we mocked it to yield once
            # The actual code: `async for changes in awatch(...)`
            # If our mock yields once and stops, the loop finishes.
            await watch_sentinel_db()
            
            mock_broadcast.assert_called_with({"type": "db_update"})

@pytest.mark.asyncio
async def test_watch_sentinel_db_error_handling():
    # Force an exception inside the loop
    with patch('backend.main.awatch', side_effect=Exception("Watch Error")):
        # Should catch and print, not raise
        await watch_sentinel_db()
        # Pass if no exception raised

# 2. Background Loops: run_witness_process
@pytest.mark.asyncio
async def test_run_witness_process_success():
    # Mock successful subprocess
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 0
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        await run_witness_process("existing_atom")
        
        # Verify DB update to 3
        conn = sqlite3.connect(TEST_DB)
        status = conn.execute("SELECT status FROM atoms WHERE id='existing_atom'").fetchone()[0]
        conn.close()
        assert status == 3

@pytest.mark.asyncio
async def test_run_witness_process_failure_exit_code():
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"Error")
    mock_proc.returncode = 1
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
        await run_witness_process("existing_atom")
        
        # Verify DB update to 1 (revert/claim) or stay 1?
        # Code: new_status = 3 if 0 else 1. So it sets to 1.
        conn = sqlite3.connect(TEST_DB)
        status = conn.execute("SELECT status FROM atoms WHERE id='existing_atom'").fetchone()[0]
        conn.close()
        assert status == 1

@pytest.mark.asyncio
async def test_run_witness_process_exception():
    with patch('asyncio.create_subprocess_exec', side_effect=OSError("Exec failed")):
        await run_witness_process("existing_atom")
        # Should catch and revert to 1
        conn = sqlite3.connect(TEST_DB)
        status = conn.execute("SELECT status FROM atoms WHERE id='existing_atom'").fetchone()[0]
        conn.close()
        assert status == 1

# 3. Error Handling: Startup/Shutdown
@pytest.mark.asyncio
async def test_lifespan_error_handling():
    # Mock sqlite3.connect to raise exception
    with patch('sqlite3.connect', side_effect=sqlite3.OperationalError("DB Fail")):
         # The lifespan context manager suppresses startup errors (prints them)
         async with lifespan(app):
             pass
         # If no raise, passed


# 4. Global Exception Handler
def test_global_exception_handler():
    # Pass raise_server_exceptions=False to allow app's exception handler to run
    # instead of TestClient re-raising the exception.
    client = TestClient(app, raise_server_exceptions=False)
    
    with patch('os.listdir', side_effect=Exception("Global Boom")):
        response = client.get("/api/workspaces")
        assert response.status_code == 500
        # Observed Schema: {'status': 'error', 'error': {'code': 'INTERNAL_ERROR', 'message': 'Global Boom', 'type': 'Exception'}}
        data = response.json()
        assert data['status'] == 'error'
        assert data['error']['message'] == 'Global Boom'



# 5. CLI Tests (Projector, Shatter)

def load_script_module(script_path):
    spec = importlib.util.spec_from_file_location("script_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_spatia_projector_cli_project():
    script_path = ".spatia/bin/spatia-projector.py"
    module = load_script_module(script_path)
    
    # Pre-seed DB with Geometry
    conn = sqlite3.connect(TEST_DB)
    # Ensure tables exist
    conn.execute("CREATE TABLE IF NOT EXISTS envelopes (id TEXT, domain TEXT, x INT, y INT, w INT, h INT)")
    conn.execute("CREATE TABLE IF NOT EXISTS threads (id TEXT, source TEXT, target TEXT)")
    conn.execute("INSERT OR REPLACE INTO geometry (atom_id, x, y) VALUES ('atom1', 10, 20)")
    conn.commit()
    conn.close()
    
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        # Reloading module to pick up env var
        module = load_script_module(script_path)
        
        with patch.object(sys, 'argv', ['spatia-projector.py', '--project']):
            if os.path.exists("geometry.sp"):
                os.remove("geometry.sp")
                
            module.main()
            
            assert os.path.exists("geometry.sp")
            with open("geometry.sp") as f:
                content = f.read()
                assert "(anchor :atom1 {x 10 y 20})" in content
            
            os.remove("geometry.sp")

def test_spatia_shatter_cli_main():
    script_path = ".spatia/bin/spatia-shatter.py"
    module = load_script_module(script_path)
    
    # Test --path basic flow
    test_file_path = "test_shatter.txt"
    with open(test_file_path, "w") as f:
        f.write("test content")
        
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        # Ensure we reload or use correct module logic. Shatter reads Env in main() now.
        with patch.object(sys, 'argv', ['spatia-shatter.py', '--path', test_file_path]):
            module.main()
            
            # Verify DB insertion
            conn = sqlite3.connect(TEST_DB)
            row = conn.execute("SELECT content FROM atoms WHERE id=?", (test_file_path,)).fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "test content"
            
    os.remove(test_file_path)

def test_spatia_init_workspace_cli():
    script_path = ".spatia/bin/spatia-init-workspace.py"
    module = load_script_module(script_path)
    
    ws_name = "test_ws_cli"
    ws_dir = os.path.join("workspaces", ws_name)
    if os.path.exists(ws_dir):
        import shutil
        shutil.rmtree(ws_dir)
        
    with patch.object(sys, 'argv', ['spatia-init-workspace.py', ws_name]):
        module.main()
        
    assert os.path.exists(os.path.join(ws_dir, "sentinel.db"))
    
    # Cleanup
    import shutil
    shutil.rmtree(ws_dir)

# 6. Deep Coverage: Unit Tests for Internal Functions (switch_workspace, sse, health)
from backend.main import switch_workspace, sse_endpoint, health_check, WorkspaceSwitch, manager

@pytest.mark.asyncio
async def test_switch_workspace_logic():
    # Helper to clean up symlink if created
    # yield # Setup done by global fixture <- REMOVED
    # We test switch_workspace by mocking everything to prevent actual FS changes if possible, 
    # OR we let it run on dummy paths.
    
    # Let's mock the critical parts to ensure logic coverage without side effects
    
    with patch('os.path.islink', return_value=True), \
         patch('os.path.exists', return_value=True), \
         patch('os.remove') as mock_remove, \
         patch('os.symlink') as mock_symlink, \
         patch('os.path.abspath', side_effect=lambda x: f"/abs/{x}"), \
         patch('os.path.relpath', return_value="rel/path"), \
         patch('backend.main.watch_sentinel_db') as mock_watch, \
         patch('backend.main.manager.broadcast', new_callable=AsyncMock) as mock_broadcast:
        
         # Mock watcher task
         class AwaitableMock(MagicMock):
             def __await__(self):
                 yield from []
                 
         mock_task = AwaitableMock()
         
         # Ensure done() and cancel() are synchronous mocks
         mock_task.done.return_value = False
         # cancel is a method
         mock_task.cancel.return_value = True
         
         backend.main.watcher_task = mock_task
         
         await switch_workspace(WorkspaceSwitch(name="target_ws"))
         
         # Verify steps
         # 1. Cancel watcher
         mock_task.cancel.assert_called()
         
         # 2. Update Symlinks (remove old, create new)
         assert mock_remove.call_count >= 2 # db and geo
         assert mock_symlink.call_count >= 2
         
         # 3. Restart watcher
         # We didn't mock create_task, so it creates a real task of the mock_watch coroutine.
         
         # 4. Broadcast
         mock_broadcast.assert_called()

@pytest.mark.asyncio
async def test_sse_endpoint_flow():
    # sse_endpoint returns a StreamingResponse
    # We want to iterate its body iterator
    
    response = await sse_endpoint()
    
    # response.body_iterator is an async generator
    # We need to simulate a client connecting
    # The generator yields "event: connected..."
    # Then waits for queue.
    
    iterator = response.body_iterator
    
    # 1. First yield: connected
    first = await iterator.__anext__()
    assert "event: connected" in first
    
    # 2. Put something in queue
    # Access backend.main.manager.clients
    async with backend.main.manager.lock:
        assert len(backend.main.manager.clients) > 0
        q = backend.main.manager.clients[0]
        
    await q.put("test_data")
    
    # 3. Second yield: data
    second = await iterator.__anext__()
    assert "test_data" in second
    
    # Clean up
    await iterator.aclose()
    
    async with backend.main.manager.lock:
        assert len(backend.main.manager.clients) == 0 # Should be removed

@pytest.mark.asyncio
async def test_health_check_coverage():
    # 1. Success case
    with patch('sqlite3.connect') as mock_connect:
        with patch('os.path.exists', return_value=True):
            mock_connect.return_value.__enter__.return_value.cursor.return_value.execute.return_value = None
            
            # Mock readlink for workspace name
            with patch('os.path.islink', return_value=True):
                 with patch('os.readlink', return_value="workspaces/test_ws/sentinel.db"):
                     res = await health_check()
                     assert res['db_status'] == 'connected'
                     assert res['workspace'] == 'test_ws'

    # 2. Error case (Exception coverage)
    with patch('sqlite3.connect', side_effect=Exception("Health Fail")):
        with patch('os.path.exists', return_value=True):
             res = await health_check()
             assert "error: Health Fail" in res['db_status']
             
    # Exception in workspace name parsing
    with patch('sqlite3.connect'):
        with patch('os.path.exists', return_value=True):
            with patch('os.path.islink', return_value=True):
                with patch('os.readlink', side_effect=Exception("Link Fail")):
                    res = await health_check()
                    assert res['workspace'] == 'unknown'

@pytest.mark.asyncio
async def test_get_envelopes_operational_error():
    # Test handling of OperationalError in get_envelopes (returns empty list)
    from backend.main import get_envelopes
    
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    
    # Simulate table missing
    cursor.execute.side_effect = sqlite3.OperationalError("Table missing")
    
    with patch('backend.main.get_db_connection', return_value=conn):
         envs = await get_envelopes()
         assert envs == []

@pytest.mark.asyncio
async def test_broadcast_event_coverage():
    # Test real broadcast iterating over clients
    # Access backend.main.manager
    
    q = await backend.main.manager.connect()
    
    await backend.main.manager.broadcast({"type": "test"})
    
    msg = await q.get()
    assert "data: " in msg
    assert '"type": "test"' in msg
    
    await backend.main.manager.disconnect(q)

@pytest.mark.asyncio
async def test_get_workspaces_logic():
    from backend.main import get_workspaces
    with patch('os.path.exists', return_value=True):
        with patch('os.listdir', return_value=["ws1", "file.txt"]):
            with patch('os.path.isdir', side_effect=lambda x: "ws1" in x):
                with patch('os.path.join', side_effect=lambda a, b: f"{a}/{b}"):
                     # ws1 has sentinel.db
                     with patch('os.path.exists', side_effect=lambda x: x.endswith("sentinel.db") or x == "workspaces"):
                         res = await get_workspaces()
                         assert "ws1" in res
                         assert "file.txt" not in res

@pytest.mark.asyncio
async def test_switch_workspace_exceptions():
    from backend.main import switch_workspace, WorkspaceSwitch
    
    # 1. Error removing links
    with patch('os.path.exists', return_value=True):
        with patch('backend.main.watcher_task', new=None): # No watcher to cancel
            with patch('os.remove', side_effect=Exception("Remove Fail")):
                 with pytest.raises(Exception) as exc: # It raises HTTPException(500)
                      await switch_workspace(WorkspaceSwitch(name="target"))
                 assert "Failed to remove symlinks" in str(exc.value.detail)

    # 2. Error creating links
    with patch('os.path.exists', return_value=True):
        with patch('backend.main.watcher_task', new=None): 
            with patch('os.remove'): # Success removal
                with patch('os.symlink', side_effect=Exception("Link Fail")):
                     with pytest.raises(Exception) as exc:
                          await switch_workspace(WorkspaceSwitch(name="target"))
                     assert "Failed to create symlinks" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_run_subprocess_async_failure():
    from backend.main import run_subprocess_async
    
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"out", b"err")
    mock_proc.returncode = 1
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_proc):
         with pytest.raises(Exception) as exc: # HTTPException
              await run_subprocess_async(["cmd"])
         assert "Script execution failed" in str(exc.value.detail)
         assert "Stderr: err" in str(exc.value.detail)

@pytest.mark.asyncio
async def test_summon_atom_edge_cases():
    from backend.main import summon_atom, SummonRequest
    
    # 1. Status != 0
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    
    # row found, but status 1
    cursor.fetchone.return_value = {"content": "c", "status": 1}
    
    with patch('backend.main.get_db_connection', return_value=conn):
        with pytest.raises(Exception) as exc:
             await summon_atom(SummonRequest(atom_id="id"), MagicMock())
        assert "Atom is not in Hollow state" in str(exc.value.detail)

    # 2. Strip code blocks
    cursor.fetchone.return_value = {"content": "c", "status": 0}
    cursor.fetchall.return_value = [] # no portals/neighbors
    
    # Projector returns ```markdown\ncontent\n```
    with patch('backend.main.get_db_connection', return_value=conn):
        with patch('backend.main.projector.summon', return_value="```markdown\nreal content\n```"):
            with patch('backend.main.run_witness_process'): 
                bg = MagicMock()
                mock_broadcast = AsyncMock()
                with patch('backend.main.manager.broadcast', mock_broadcast):
                    # also mock open() so we don't write to disk
                    with patch('builtins.open', new_callable=MagicMock):
                        await summon_atom(SummonRequest(atom_id="id"), bg)
            
            # Verify update call stripped the blocks
            update_call = [call for call in cursor.execute.call_args_list if "UPDATE atoms SET content" in call[0][0]]
            assert update_call
            assert update_call[0][0][1][0] == "real content"

def test_get_portals(client):
    # Just basic coverage
    resp = client.get("/api/portals/existing_atom")
    assert resp.status_code == 200
    assert resp.json() == []

# =================================================================================================
# NEW TESTS FOR COVERAGE GAPS (Projector Init, Summon Exceptions, Workspace Validation, Clone Race)
# =================================================================================================

# --- Projector Tests ---

def test_projector_initialization_warning(capsys):
    """
    Test that Projector prints a warning when GEMINI_API_KEY is not set.
    """
    with patch.dict(os.environ, {}, clear=True):
        proj = backend.projector.Projector()
        assert proj.client is None
        
        captured = capsys.readouterr()
        assert "WARNING: GEMINI_API_KEY not set" in captured.out

def test_projector_summon_without_client():
    """
    Test summon returns specific error string when client is None
    """
    proj = backend.projector.Projector()
    proj.client = None # Force ensure
    
    result = proj.summon("id", "content", [], [])
    assert ";; Error: GEMINI_API_KEY not set." in result

def test_projector_summon_genai_exception():
    """
    Test summon handles generic exceptions from genai client
    """
    proj = backend.projector.Projector()
    proj.client = MagicMock()
    
    # Mock gather_aura to return tuple
    with patch.object(proj, 'gather_aura', return_value=("sys", "user")):
        # Mock generate_content to raise
        proj.client.models.generate_content.side_effect = Exception("API Error")
        
        result = proj.summon("id", "content", [], [])
        assert ";; Error during summoning: API Error" in result

def test_projector_summon_empty_response():
    """
    Test summon handles empty response text
    """
    proj = backend.projector.Projector()
    proj.client = MagicMock()
    
    with patch.object(proj, 'gather_aura', return_value=("sys", "user")):
        mock_resp = MagicMock()
        mock_resp.text = None # Empty result
        proj.client.models.generate_content.return_value = mock_resp
        
        result = proj.summon("id", "content", [], [])
        assert ";; Error: No content generated." in result

# --- Workspace Tests ---

def test_create_workspace_invalid_names():
    """
    Test invalid names: '..', '/', empty, etc.
    """
    invalid_names = ["..", ".", "foo/bar", "foo\\bar", ""]
    for name in invalid_names:
        resp = client.post("/api/workspaces", json={"name": name})
        assert resp.status_code == 400
        data = resp.json()
        # Handle potential schema variation
        msg = data.get('detail') or (data.get('error', {}).get('message'))
        assert "Invalid workspace name" in msg

@pytest.mark.asyncio
async def test_clone_workspace_collision_handling():
    """
    Test auto-renaming when target exists.
    """
    from backend.main import clone_workspace, CloneRequest
    
    with patch('os.path.isdir', return_value=True): # src exists
        def side_effect_exists(path):
            if path.endswith("ws1-copy"): return True
            if path.endswith("ws1-copy-1"): return False
            return False
            
        with patch('os.path.exists', side_effect=side_effect_exists):
            with patch('shutil.copytree') as mock_copy:
                 # Must pass req=None to avoid Body(...) default object
                 res = await clone_workspace("ws1", req=None)
                 
                 assert res['target'] == "ws1-copy-1"
                 mock_copy.assert_called_with('workspaces/ws1', 'workspaces/ws1-copy-1')

@pytest.mark.asyncio
async def test_clone_workspace_explicit_collision():
    """
    Test 409 when explicit new_name exists.
    """
    from backend.main import clone_workspace, CloneRequest
    
    with patch('os.path.isdir', return_value=True):
        with patch('os.path.exists', return_value=True): # Target exists
             with pytest.raises(Exception) as exc:
                 await clone_workspace("ws1", CloneRequest(new_name="conflict"))
             assert exc.value.status_code == 409

@pytest.mark.asyncio
async def test_clone_workspace_copy_failure():
    """
    Test 500 when shutil.copytree fails.
    """
    from backend.main import clone_workspace
    
    with patch('os.path.isdir', return_value=True):
        with patch('os.path.exists', return_value=False):
             with patch('shutil.copytree', side_effect=Exception("Disk Full")):
                 with pytest.raises(Exception) as exc:
                     await clone_workspace("ws1", req=None)
                 assert exc.value.status_code == 500

# --- Additional Gaps Coverage ---

@pytest.mark.asyncio
async def test_snapshot_workspace_error_cases():
    from backend.main import snapshot_workspace
    
    # 1. 404 Workspace Not Found (line 256)
    with patch('os.path.isdir', side_effect=lambda x: False):
        with pytest.raises(Exception) as exc:
            await snapshot_workspace("missing_ws")
        assert exc.value.status_code == 404
        assert "Workspace not found" in exc.value.detail

    # 2. 404 DB Not Found (line 260)
    with patch('os.path.isdir', return_value=True):
        with patch('os.path.exists', return_value=False): # DB check
             with pytest.raises(Exception) as exc:
                 await snapshot_workspace("valid_ws")
             assert exc.value.status_code == 404
             assert "Sentinel DB not found" in exc.value.detail

    # 3. 500 Copy Fail (lines 267-268)
    with patch('os.path.isdir', return_value=True):
        with patch('os.path.exists', return_value=True):
            with patch('shutil.copy2', side_effect=Exception("Copy Fail")):
                with pytest.raises(Exception) as exc:
                    await snapshot_workspace("valid_ws")
                assert exc.value.status_code == 500
                assert "Failed to snapshot" in exc.value.detail

@pytest.mark.asyncio
async def test_switch_workspace_not_found():
    from backend.main import switch_workspace, WorkspaceSwitch
    # Line 177
    with patch('os.path.exists', return_value=False):
         with pytest.raises(Exception) as exc:
             await switch_workspace(WorkspaceSwitch(name="missing"))
         assert exc.value.status_code == 404
         assert "Workspace not found" in exc.value.detail

def test_get_db_connection_missing():
    from backend.main import get_db_connection
    # Line 418
    # We must patch DB_PATH or os.path.exists using the module imported name
    with patch('backend.main.DB_PATH', "missing.db"):
         with patch('os.path.exists', return_value=False):
             with pytest.raises(Exception) as exc:
                 get_db_connection()
             assert exc.value.status_code == 500
             assert "Sentinel DB not found" in exc.value.detail

@pytest.mark.asyncio
async def test_shatter_no_output_id():
    from backend.main import shatter_atom, ShatterRequest, SHATTER_SCRIPT
    # Line 444: if not atom_id
    
    # Mock run_subprocess_async to return output without ATOM_ID:
    with patch('backend.main.run_subprocess_async', return_value="Some output but no ID"):
         with pytest.raises(Exception) as exc:
             await shatter_atom(ShatterRequest(path="foo"))
         assert exc.value.status_code == 500
         assert "Could not determine atom_id" in exc.value.detail

@pytest.mark.asyncio
async def test_summon_atom_write_disk():
    from backend.main import summon_atom, SummonRequest
    
    # Lines 588-589: if os.path.exists(atom_id): write...
    
    conn = MagicMock()
    conn.cursor.return_value.fetchone.return_value = {"content": "c", "status": 0}
    conn.cursor.return_value.fetchall.return_value = []
    conn.__enter__.return_value = conn
    
    with patch('backend.main.get_db_connection', return_value=conn):
        with patch('backend.main.projector.summon', return_value="new content"):
            with patch('os.path.exists', return_value=True):
                 with patch('builtins.open', new_callable=MagicMock) as mock_open:
                     # Mock background tasks
                     bg = MagicMock()
                     # Mock broadcast
                     with patch('backend.main.manager.broadcast', new_callable=AsyncMock):
                          await summon_atom(SummonRequest(atom_id="file.md"), bg)
                          
                     mock_open.assert_called_with("file.md", "w")
                     mock_open.return_value.__enter__.return_value.write.assert_called_with("new content")

@pytest.mark.asyncio
async def test_revive_atom_errors():
    from backend.main import revive_atom, ReviveRequest
    
    # 1. Invalid ID format (line 680)
    with pytest.raises(Exception) as exc:
        await revive_atom(ReviveRequest(fossil_id="bad_id"))
    assert exc.value.status_code == 400
    
    # 2. Fossil not found (line 691)
    conn = MagicMock()
    conn.cursor.return_value.fetchone.return_value = None
    conn.__enter__.return_value = conn
    
    with patch('backend.main.get_db_connection', return_value=conn):
        with pytest.raises(Exception) as exc:
             await revive_atom(ReviveRequest(fossil_id="id@ts"))
        assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_get_atom_logs_error():
    from backend.main import get_atom_logs
    
    # Lines 765-766
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', side_effect=Exception("Read Fail")):
             with pytest.raises(Exception) as exc:
                 await get_atom_logs("atom1")
             assert exc.value.status_code == 500

@pytest.mark.asyncio
async def test_sse_endpoint_cancelled():
    # Test cancellation using ConnectionManager
    # We can connect, then inspect clients list, then clean up
    # In integration test we cancel, but here we cover the finally block
    
    response = await sse_endpoint()
    iterator = response.body_iterator
    
    # Connect
    await iterator.__anext__()
    
    # Simulate Cancel
    try:
        await iterator.athrow(asyncio.CancelledError)
    except:
        pass
    
    # Check manager clients is empty
    async with backend.main.manager.lock:
        assert len(backend.main.manager.clients) == 0

@pytest.mark.asyncio
async def test_clone_workspace_not_found():
    from backend.main import clone_workspace
    # Line 279
    with patch('os.path.isdir', return_value=False):
         with pytest.raises(Exception) as exc:
             await clone_workspace("missing_ws")
         assert exc.value.status_code == 404
         assert "Workspace not found" in exc.value.detail

@pytest.mark.asyncio
async def test_summon_atom_not_found():
    from backend.main import summon_atom, SummonRequest
    # Line 551
    conn = MagicMock()
    conn.cursor.return_value.fetchone.return_value = None
    conn.__enter__.return_value = conn
    
    with patch('backend.main.get_db_connection', return_value=conn):
         with pytest.raises(Exception) as exc:
             await summon_atom(SummonRequest(atom_id="missing"), MagicMock())
         assert exc.value.status_code == 404
         assert "Atom not found" in exc.value.detail
