import os
import pytest
from fastapi.testclient import TestClient
import sqlite3
import backend.main
from backend.main import app

client = TestClient(app)
TEST_DB = "test_sentinel.db"

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: Override DB_PATH
    backend.main.DB_PATH = TEST_DB
    os.environ["SENTINEL_DB"] = TEST_DB
    if os.path.lexists(TEST_DB):
        os.remove(TEST_DB)
    
    # Initialize DB schema (Partial for what we need)
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE atoms (id TEXT PRIMARY KEY, path TEXT, content TEXT, hash TEXT, domain TEXT, status INTEGER, parent_id TEXT, timestamp TEXT)")
    
    # Insert test atoms
    # 1. Success Candidate
    cursor.execute("INSERT INTO atoms VALUES ('test_atom_success', 'path/a', 'print(\"hello\")', 'hash', 'software', 1, NULL, 'now')")
    # 2. Failure Candidate (Syntax Error)
    cursor.execute("INSERT INTO atoms VALUES ('test_atom_fail', 'path/b', 'print(\"oops\"', 'hash', 'software', 1, NULL, 'now')")
    # 3. Lisp Intent Candidate (Should Pass now)
    cursor.execute("INSERT INTO atoms VALUES ('test_atom_lisp', 'path/c', ':intent \"To verify\" (defun foo ())', 'hash', 'software', 1, NULL, 'now')")
    
    conn.commit()
    conn.close()
    
    yield
    
    # Teardown
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_witness_success_flow():
    """Test full cycle: Claim (1) -> Witness (2) -> Endorsed (3)"""
    
    # 1. Call Witness
    # Note: TestClient waits for background tasks to complete by default
    print("\n[TEST] Sending proper witness request...")
    response = client.post("/api/witness", json={"atom_id": "test_atom_success"})
    
    assert response.status_code == 200
    assert response.json() == {"status": "witnessing", "atom_id": "test_atom_success"}
    
    # 2. Verify Final Status
    # Since background task ran synchronously in TestClient, status should be 3 now
    with sqlite3.connect(TEST_DB) as conn:
        status = conn.execute("SELECT status FROM atoms WHERE id='test_atom_success'").fetchone()[0]
        print(f"[TEST] Final Status for success atom: {status}")
        assert status == 3

def test_witness_failure_flow():
    """Test cycle: Claim (1) -> Witness (2) -> Failure -> Claim (1)"""
    
    print("\n[TEST] Sending failing witness request...")
    response = client.post("/api/witness", json={"atom_id": "test_atom_fail"})
    assert response.status_code == 200
    
    # Verify Revert to 1
    with sqlite3.connect(TEST_DB) as conn:
        status = conn.execute("SELECT status FROM atoms WHERE id='test_atom_fail'").fetchone()[0]
        print(f"[TEST] Final Status for fail atom: {status}")
        assert status == 1

def test_witness_lisp_intent():
    """Test Intent: Claim (1) -> Witness (2) -> Endorsed (3) [Skipped Python Check]"""
    
    print("\n[TEST] Sending witness request for Lisp Intent...")
    response = client.post("/api/witness", json={"atom_id": "test_atom_lisp"})
    
    assert response.status_code == 200
    assert response.json() == {"status": "witnessing", "atom_id": "test_atom_lisp"}
    
    # 2. Verify Final Status
    with sqlite3.connect(TEST_DB) as conn:
        status = conn.execute("SELECT status FROM atoms WHERE id='test_atom_lisp'").fetchone()[0]
        print(f"[TEST] Final Status for lisp atom: {status}")
        assert status == 3
