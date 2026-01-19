import os
import pytest
from fastapi.testclient import TestClient
import sqlite3
import backend.main
from backend.main import app

client = TestClient(app)
TEST_DB = "test_sentinel_summon.db"

@pytest.fixture(autouse=True)
def setup_teardown():
    backend.main.DB_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Initialize DB (Schema)
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE atoms (id TEXT PRIMARY KEY, type TEXT, content TEXT, hash TEXT, domain TEXT DEFAULT 'generic', status INTEGER DEFAULT 0, parent_project TEXT, last_witnessed TEXT)")
    cursor.execute("CREATE TABLE portals (id INTEGER PRIMARY KEY AUTOINCREMENT, atom_id TEXT, path TEXT, description TEXT, created_at TEXT)")
    cursor.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, source TEXT, target TEXT)")
    # Also geometry needed for other lookups? Not for summon.
    cursor.execute("CREATE TABLE geometry (atom_id TEXT, pane_id TEXT, x INTEGER, y INTEGER)")
    cursor.execute("CREATE UNIQUE INDEX idx_geometry_atom_id ON geometry(atom_id)")
    
    conn.commit()
    conn.close()
    
    yield
    
    # 3. Teardown
    backend.main.DB_PATH = '.spatia/sentinel.db' # Revert to default
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_summoning_flow():
    from unittest.mock import MagicMock, patch
    
    # Mock the instance method on the global object
    with patch('backend.main.projector.summon', return_value=";; SUMMONED BY SPATIA\n(implementation details)"):
        # 1. Create Hollow Atom
        with sqlite3.connect(TEST_DB) as conn:
            conn.execute("INSERT INTO atoms (id, status, content) VALUES ('hollow_atom', 0, ':intent \"Fix bugs\"')")
            conn.commit()
            
        # 2. Add Portal
        res = client.post("/api/portals", json={"atom_id": "hollow_atom", "path": "/etc/nixos/configuration.nix"})
        assert res.status_code == 200
        
        # 3. Summon
        res = client.post("/api/summon", json={"atom_id": "hollow_atom"})
        if res.status_code != 200:
            print(f"Summon failed: {res.json()}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "summoned"
        
        # 4. Verification
        with sqlite3.connect(TEST_DB) as conn:
            row = conn.execute("SELECT status, content FROM atoms WHERE id='hollow_atom'").fetchone()
            status, content = row[0], row[1]
            
            print(f"Status after summon: {status}")
            print(f"Content after summon: {content}")
            
            assert status != 0
            # Mock is active, so we strictly expect this content
            assert ";; SUMMONED BY SPATIA" in content, f"Unexpected content: {content}"
        


def test_summoning_fail_if_not_hollow():
    with sqlite3.connect(TEST_DB) as conn:
        conn.execute("INSERT INTO atoms (id, status, content) VALUES ('filled_atom', 1, 'code')")
        conn.commit()
    
    res = client.post("/api/summon", json={"atom_id": "filled_atom"})
    assert res.status_code == 400
