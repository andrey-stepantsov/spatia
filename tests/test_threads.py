import pytest
from fastapi.testclient import TestClient
from backend import main
from unittest.mock import patch
import os
import sqlite3
import subprocess

# Override DB Path for testing
TEST_DB = "test_threads.db"

# We must import app AFTER patching if we were doing module level patch, 
# but simply importing it is fine if we patch the attribute on `main`.
from backend.main import app

@pytest.fixture(autouse=True)
def setup_database():
    # Patch DB_PATH for the duration of the test
    with patch('backend.main.DB_PATH', TEST_DB):
        # Setup
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE atoms (id TEXT PRIMARY KEY, type TEXT, content TEXT, hash TEXT, domain TEXT, status INTEGER)")
        cursor.execute("CREATE TABLE geometry (atom_id TEXT, pane_id TEXT, x INTEGER, y INTEGER)")
        cursor.execute("CREATE UNIQUE INDEX idx_geometry_atom_id ON geometry(atom_id)")
        cursor.execute("CREATE TABLE threads (source_id TEXT, target_id TEXT, PRIMARY KEY (source_id, target_id))")
        conn.commit()
        conn.close()
        
        yield
        
        # Teardown
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

client = TestClient(app)

def test_create_and_get_threads():
    # Create a thread
    response = client.post("/api/threads", json={"source": "atomA", "target": "atomB"})
    assert response.status_code == 200, f"Response: {response.text}"
    assert response.json() == {"status": "ok"}
    
    # Get threads
    response = client.get("/api/threads")
    assert response.status_code == 200, f"Response: {response.text}"
    threads = response.json()
    assert len(threads) == 1
    assert threads[0]["source"] == "atomA"
    assert threads[0]["target"] == "atomB"

def test_duplicate_thread_ignored():
    client.post("/api/threads", json={"source": "atomA", "target": "atomB"})
    response = client.post("/api/threads", json={"source": "atomA", "target": "atomB"})
    assert response.status_code == 200 # Should be idempotent/ok
    
    response = client.get("/api/threads")
    assert len(response.json()) == 1

def test_geometry_projection_integration():
    # Insert some data into the test DB
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO geometry (atom_id, x, y) VALUES ('atom1', 10, 20)")
    cursor.execute("INSERT INTO threads (source_id, target_id) VALUES ('atom1', 'atom2')")
    conn.commit()
    conn.close()
    
    # We need to run the projector script but point it to our TEST_DB
    # The script reads SENTINEL_DB env var.
    env = os.environ.copy()
    env["SENTINEL_DB"] = TEST_DB
    
    # 1. Project
    cmd = [".spatia/bin/spatia-projector.py", "--project"]
    result = subprocess.run(cmd, env=env, text=True, capture_output=True)
    assert result.returncode == 0
    assert "(anchor :atom1 {x 10 y 20})" in open("geometry.sp").read()
    assert "(thread :atom1 :atom2)" in open("geometry.sp").read()
    
    # 2. Modify geometry.sp
    with open("geometry.sp", "a") as f:
        f.write("\n(thread :atom3 :atom4)\n")
        
    # 3. Shatter back
    cmd = [".spatia/bin/spatia-projector.py", "--shatter"]
    result = subprocess.run(cmd, env=env, text=True, capture_output=True)
    assert result.returncode == 0
    
    # 4. Verify DB updated
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM threads WHERE source_id='atom3'")
    row = cursor.fetchone()
    assert row is not None
    assert row[1] == 'atom4'
    conn.close()
    
    # Cleanup generated file
    if os.path.exists("geometry.sp"):
        os.remove("geometry.sp")
