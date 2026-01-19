import pytest
from fastapi.testclient import TestClient
import backend.main
from backend.main import app
import sqlite3
import os
import time

TEST_DB = "test_sentinel_legal.db"

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    # Patch DB Path
    original_db = backend.main.DB_PATH
    backend.main.DB_PATH = TEST_DB
    os.environ["SENTINEL_DB"] = TEST_DB
    
    if os.path.lexists(TEST_DB):
        os.remove(TEST_DB)
        
    # Trigger startup to init DB
    with TestClient(app) as _:
        yield

    # Teardown
    backend.main.DB_PATH = original_db
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_witness_legal_success():
    # 1. Create Atom with "SECTION"
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    atom_id = "legal_pass.contract"
    content = "SECTION 1. This is a valid contract."
    cursor.execute(
        "INSERT INTO atoms (id, type, domain, content, status, hash, last_witnessed) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (atom_id, 'file', 'Legal', content, 1, 'hash', 'now')
    )
    conn.commit()
    conn.close()

    # 2. Trigger Witness
    response = client.post("/api/witness", json={"atom_id": atom_id})
    assert response.status_code == 200
    assert response.json()["status"] == "witnessing"
    
    # 3. Wait for background task
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
    assert "Legal Check Passed" in logs

def test_witness_legal_failure():
    # 1. Create Atom WITHOUT "SECTION"
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    atom_id = "legal_fail.contract"
    content = "This is just a random text without the keyword."
    cursor.execute(
        "INSERT INTO atoms (id, type, domain, content, status, hash, last_witnessed) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (atom_id, 'file', 'Legal', content, 1, 'hash', 'now')
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
            
    assert final_status == 1 # Reverted to Claim on failure
    
    # 4. Verify Logs
    response = client.get(f"/api/atoms/{atom_id}/logs")
    assert response.status_code == 200
    logs = response.json()["logs"]
    assert "Legal Check Failed" in logs
