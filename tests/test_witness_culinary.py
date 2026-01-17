import pytest
from fastapi.testclient import TestClient
import backend.main
from backend.main import app
import sqlite3
import os
import time

TEST_DB = "test_sentinel_culinary.db"

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    # Patch DB Path
    original_db = backend.main.DB_PATH
    backend.main.DB_PATH = TEST_DB
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    # Trigger startup to init DB
    with TestClient(app) as _:
        yield

    # Teardown
    backend.main.DB_PATH = original_db
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_witness_culinary_success():
    # 1. Create Atom with length 7
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    atom_id = "culinary_pass.txt"
    content = "1234567" # Length 7
    cursor.execute(
        "INSERT INTO atoms (id, type, domain, content, status, hash, last_witnessed) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (atom_id, 'file', 'Culinary', content, 1, 'hash', 'now')
    )
    conn.commit()
    conn.close()

    # 2. Trigger Witness
    response = client.post("/api/witness", json={"atom_id": atom_id})
    assert response.status_code == 200
    assert response.json()["status"] == "witnessing"
    
    # 3. Wait for background task (poll status)
    status = None
    for _ in range(20):
        time.sleep(0.5)
        conn = sqlite3.connect(TEST_DB)
        cur = conn.cursor()
        cur.execute("SELECT status FROM atoms WHERE id = ?", (atom_id,))
        row = cur.fetchone()
        status = row[0] if row else None
        conn.close()
        if status == 3: # Endorsed
            break
    
    assert status == 3
    
    # 4. Verify Logs
    response = client.get(f"/api/atoms/{atom_id}/logs")
    assert response.status_code == 200
    logs = response.json()["logs"]
    assert "Math Check Passed" in logs

def test_witness_culinary_failure():
    # 1. Create Atom with length 6
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    atom_id = "culinary_fail.txt"
    content = "123456" # Length 6
    cursor.execute(
        "INSERT INTO atoms (id, type, domain, content, status, hash, last_witnessed) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (atom_id, 'file', 'Culinary', content, 1, 'hash', 'now')
    )
    conn.commit()
    conn.close()

    # 2. Trigger Witness
    response = client.post("/api/witness", json={"atom_id": atom_id})
    assert response.status_code == 200

    # 3. Wait for background task
    final_status = None
    for _ in range(20):
        time.sleep(0.5)
        conn = sqlite3.connect(TEST_DB)
        cur = conn.cursor()
        cur.execute("SELECT status FROM atoms WHERE id = ?", (atom_id,))
        row = cur.fetchone()
        final_status = row[0] if row else None
        conn.close()
        if final_status != 2: # Changed from witnessing
            break
            
    # Should revert to 1 (Claim) on failure (or maybe stay 1 if it flips 2->1)
    # main.py sets it to 1 if exit code != 0
    assert final_status == 1 
    
    # 4. Verify Logs
    response = client.get(f"/api/atoms/{atom_id}/logs")
    assert response.status_code == 200
    logs = response.json()["logs"]
    assert "Math Check Failed" in logs
