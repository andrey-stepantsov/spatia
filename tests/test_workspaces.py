import pytest
import os
import shutil
import asyncio
from fastapi.testclient import TestClient
from backend.main import app, DB_PATH
import backend.main as main_module

client = TestClient(app)

# Fixture to setup/teardown workspaces environment
@pytest.fixture(autouse=True)
def setup_workspaces():
    # Setup
    os.makedirs("workspaces/test_ws_a", exist_ok=True)
    os.makedirs("workspaces/test_ws_b", exist_ok=True)
    
    # Create valid sentinel.db in each
    with open("workspaces/test_ws_a/sentinel.db", "w") as f:
        f.write("")
    with open("workspaces/test_ws_b/sentinel.db", "w") as f:
        f.write("")
    with open("workspaces/test_ws_a/geometry.sp", "w") as f:
        f.write("")
    with open("workspaces/test_ws_b/geometry.sp", "w") as f:
        f.write("")

    # Ensure .spatia exists
    os.makedirs(".spatia", exist_ok=True)
    
    # Save original symlinks if any
    orig_db_link = None
    orig_geo_link = None
    if os.path.islink(DB_PATH):
        orig_db_link = os.readlink(DB_PATH)
    if os.path.islink(".spatia/geometry.sp"):
        orig_geo_link = os.readlink(".spatia/geometry.sp")
        
    yield
    
    # Teardown
    shutil.rmtree("workspaces/test_ws_a")
    shutil.rmtree("workspaces/test_ws_b")
    
    # Restore symlinks if possible (mocked)
    if os.path.exists(DB_PATH) or os.path.islink(DB_PATH):
        os.remove(DB_PATH)
    if os.path.exists(".spatia/geometry.sp") or os.path.islink(".spatia/geometry.sp"):
        os.remove(".spatia/geometry.sp")
        
    if orig_db_link:
        os.symlink(orig_db_link, DB_PATH)
    if orig_geo_link:
        os.symlink(orig_geo_link, ".spatia/geometry.sp")

def test_get_workspaces():
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert "test_ws_a" in data
    assert "test_ws_b" in data

def test_switch_workspace():
    # Since TestClient is synchronous but the endpoint is async and modifies global state (watcher),
    # we need to be careful. The TestClient runs the app in the same process potentially.
    # However, the `watcher_task` logic uses `asyncio.create_task` which requires a loop.
    # TestClient starts its own loop or uses the existing one?
    # Actually, for async endpoints modifying background tasks, it's better to use AsyncClient or mock the side effects.
    # But let's try calling the endpoint.
    
    # Mock broadcast_event to avoid queue errors if no clients connected
    main_module.clients = [] 
    
    # Check initial symlink (might be missing if we just started)
    # create a dummy default
    if not os.path.exists(DB_PATH):
        os.symlink("../workspaces/test_ws_a/sentinel.db", DB_PATH)
        
    response = client.post("/api/workspace/switch", json={"name": "test_ws_b"})
    assert response.status_code == 200
    assert response.json()["workspace"] == "test_ws_b"
    
    # Verify symlink update
    # Note: DB_PATH might be patched by conftest, so check backend.main.DB_PATH
    current_db_path = main_module.DB_PATH
    assert os.path.islink(current_db_path)
    target = os.readlink(current_db_path)
    assert "test_ws_b" in target
    
    assert os.path.islink(".spatia/geometry.sp")
    geo_target = os.readlink(".spatia/geometry.sp")
    assert "test_ws_b" in geo_target
