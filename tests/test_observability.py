
import pytest
import asyncio
import time
import os
import httpx
import sqlite3
from backend.main import app

@pytest.fixture(scope="module")
def server_url():
    # Start server in a separate process using subprocess for better isolation
    import subprocess
    import sys
    
    env = os.environ.copy()
    env["WITNESS_SCRIPT"] = "/usr/bin/true"
    env["PYTHONUNBUFFERED"] = "1"
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8002"],
        env=env,
        text=True
    )
    
    # Wait for server to come up
    url = "http://127.0.0.1:8002"
    timeout = 60
    start_time = time.time()
    while time.time() - start_time < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f"Server process died unexpectedly with code {proc.returncode}")
            
        try:
            import requests
            requests.get(f"{url}/docs")
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("Server failed to start within timeout.")
        
    yield url
    
    # Cleanup
    proc.terminate()
    try:
        proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.mark.anyio
async def test_observability_events(server_url):
    """
    Verify that actions trigger expected events for the frontend log panel.
    """
    print(f"Connecting to {server_url}/api/events")
    
    # We will collect events in this list
    collected_events = []
    
    async def listen_sse():
        async with httpx.AsyncClient(base_url=server_url, timeout=10.0) as ac:
            async with ac.stream("GET", "/api/events") as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        try:
                            data = json.loads(line[6:])
                            collected_events.append(data)
                        except:
                            pass
                            
    # Start Listener in Background
    listener_task = asyncio.create_task(listen_sse())
    
    # Wait a bit for connection
    await asyncio.sleep(1)
    
    # 1. Trigger Thread Creation (should fire 'thread_new')
    async with httpx.AsyncClient(base_url=server_url) as ac:
        res = await ac.post("/api/threads", json={"source": "obs_1", "target": "obs_2"})
        assert res.status_code == 200
        
    # Wait for event
    await asyncio.sleep(1)
    
    # 2. Trigger Envelope Creation (should fire 'envelope_update')
    unique_id = f"obs_env_{int(time.time())}"
    async with httpx.AsyncClient(base_url=server_url) as ac:
        res = await ac.post("/api/envelopes", json={
            "id": unique_id, "domain": "test", "x": 0, "y": 0, "w": 100, "h": 100
        })
        assert res.status_code == 200

    # Wait for event
    await asyncio.sleep(1)

    # Stop listener
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
        
    print("Collected Events:", collected_events)
    
    # Verify Events
    event_types = [e.get("type") for e in collected_events]
    
    assert "thread_new" in event_types, "Missing thread_new event"
    assert "envelope_update" in event_types, "Missing envelope_update event"
