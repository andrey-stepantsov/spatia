import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from backend.main import app, DB_PATH

client = TestClient(app)
TEST_DB = "test_coverage.db"

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup test DB
    import backend.main
    backend.main.DB_PATH = TEST_DB
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    # Schema matches main.py expectations
    cursor.execute("CREATE TABLE atoms (id TEXT PRIMARY KEY, status INTEGER)")
    cursor.execute("INSERT INTO atoms VALUES ('existing_atom', 1)")
    conn.commit()
    conn.close()
    
    # Setup Logs Directory
    os.makedirs(".spatia/logs", exist_ok=True)
    with open(".spatia/logs/existing_atom.log", "w") as f:
        f.write("Log content")
    
    yield
    
    # Teardown
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    if os.path.exists(".spatia/logs/existing_atom.log"):
        os.remove(".spatia/logs/existing_atom.log")

def test_get_logs_success():
    response = client.get("/api/atoms/existing_atom/logs")
    assert response.status_code == 200
    assert response.json()["logs"] == "Log content"

def test_get_logs_not_found():
    response = client.get("/api/atoms/non_existent_atom/logs")
    assert response.status_code == 404

def test_witness_404():
    response = client.post("/api/witness", json={"atom_id": "ghost_atom"})
    assert response.status_code == 404
    assert "Atom not found" in response.json()["detail"]

@patch('backend.main.broadcast_event', new_callable=AsyncMock)
def test_witness_broadcasts_event(mock_broadcast):
    # Verify that calling witness triggers a broadcast
    response = client.post("/api/witness", json={"atom_id": "existing_atom"})
    
    assert response.status_code == 200
    # It should have been called twice: 
    # 1. Immediate update (Status 2)
    # 2. Start of background (optional redundancy) or 
    # 3. completion (Status 3/1) -- BUT background tasks run after response in FastAPI?
    # TestClient triggers background tasks synchronously AFTER the request.
    
    # We expect multiple calls.
    assert mock_broadcast.call_count >= 1
    
    # Inspect arguments of first call
    args, _ = mock_broadcast.call_args_list[0]
    assert args[0] == {"type": "update", "atom_id": "existing_atom"}
