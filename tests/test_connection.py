import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from backend.main import app
import os
import sqlite3

# Test Configuration
BASE_URL = "http://test"

@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        response = await ac.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "workspace" in data
    assert "db_status" in data

@pytest.mark.asyncio
async def test_global_exception_handler(monkeypatch):
    # Mock an endpoint to raise a generic exception
    # Since we can't easily modify the app routes dynamically in a robust way for just one test without
    # potentially side-effecting, we'll try to trigger an error in an existing one or rely on
    # a new testing route.
    # A safer way is to mock a function that an endpoint calls.
    
    async def mock_shatter_subprocess(*args, **kwargs):
        raise RuntimeError("Simulated Subprocess Crash")
    
    # Patch the run_subprocess_async which is used by /api/shatter
    from backend import main
    monkeypatch.setattr(main, "run_subprocess_async", mock_shatter_subprocess)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        response = await ac.post("/api/shatter", json={"path": "test", "content": "test"})
        
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    # Shatter endpoint catches exceptions and wraps in HTTPException, so we expect HTTP_ERROR
    assert data["error"]["code"] == "HTTP_ERROR"
    assert "Simulated Subprocess Crash" in data["error"]["message"]

@pytest.mark.asyncio
async def test_http_exception_handler():
    # Trigger a 404
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        response = await ac.get("/api/non_existent_endpoint")
        
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "HTTP_ERROR"
