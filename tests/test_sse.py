import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_sse_endpoint(client):
    print("Test Started")
    # assert False
    # client = TestClient(app) # Use fixture instead
    with client.stream("GET", "/api/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Iterate to receive the first event
        for line in response.iter_lines():
            if line:
                print(f"Received: {line}")
                assert b"event: connected" in line or b"data: {}" in line
                break

