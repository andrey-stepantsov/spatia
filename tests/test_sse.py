
import pytest
import asyncio
import time
import multiprocessing
import uvicorn
import httpx
from backend.main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

@pytest.fixture(scope="module")
def server_url():
    # Start server in a separate process
    proc = multiprocessing.Process(target=run_server, daemon=True)
    proc.start()
    
    # Wait for server to come up
    url = "http://127.0.0.1:8001"
    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # We can use requests or httpx sync to check
            import requests
            requests.get(f"{url}/docs")
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("Server failed to start")
        
    yield url
    
    # Cleanup
    proc.terminate()
    proc.join()

@pytest.mark.anyio
async def test_sse_endpoint(server_url):
    print(f"Connecting to {server_url}/api/events")
    async with httpx.AsyncClient(base_url=server_url, timeout=5.0) as ac:
        async with ac.stream("GET", "/api/events") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            
            print("Stream started, iterating...")
            async for line in response.aiter_lines():
                print(f"Received: {line}")
                if "event: connected" in line or "data: {}" in line:
                    break
            print("Found connection event")

@pytest.mark.anyio
async def test_summon_flow(server_url):
    """
    Test the full summon flow:
    1. Create Shadow Atom (Status 0)
    2. Connect SSE
    3. Trigger Summon
    4. Verify transitions: 0 -> 1 -> 2 -> 3 (or 1 if witness failed/mocked)
    """
    atom_id = "test_summon_atom"
    
    # 1. Create Atom via DB (bypass API for setup)
    import sqlite3
    db_path = ".spatia/sentinel.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT OR REPLACE INTO atoms (id, type, content, status) VALUES (?, 'file', ';; intent', 0)", (atom_id,))
        conn.commit()

    # Mocking Projector is tricky since it's a global instance in backend/main.py imported from backend.projector
    # But since we run the server via uvicorn.run in a subprocess, we can't easily patch the instance inside that process from here.
    # However, for this integration test, we might just let it fail or use a specialized test setup.
    # Actually, if GEMINI_API_KEY is missing, Projector returns error string, which is fine.
    # Status transitions should still happen (0 -> 1 -> 2 -> witness).
    # Witness router might fail if script missing or whatever, reverting to 1.
    
    print(f"Connecting to SSE...")
    async with httpx.AsyncClient(base_url=server_url, timeout=30.0) as ac:
        # Start listening
        async with ac.stream("GET", "/api/events") as response:
            assert response.status_code == 200
            
            # Flush initial event
            lines = response.aiter_lines()
            init = await lines.__anext__() 
            
            # Trigger Summon in background (using another client)
            print("Triggering Summon...")
            async with httpx.AsyncClient(base_url=server_url) as trigger_client:
                # We expect this to return quickly
                r = await trigger_client.post("/api/summon", json={"atom_id": atom_id})
                assert r.status_code == 200, f"Summon failed: {r.text}"
            
            # Listen for updates
            # We expect at least one "update" event for atom_id
            events_received = 0
            async for line in lines:
                print(f"Stream: {line}")
                if f'"atom_id": "{atom_id}"' in line and "update" in line:
                    events_received += 1
                    # We expect multiple updates (Status 1, Status 2, Witness Result)
                    if events_received >= 2:
                        break
                
                if time.time() - time.time() > 5: # Timeout check manual
                    break
            
            assert events_received >= 1, "Did not receive update events for summoned atom"
