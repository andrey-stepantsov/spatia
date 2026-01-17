
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
