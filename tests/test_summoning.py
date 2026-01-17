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
    # Clean up logs
    if os.path.exists(".spatia/logs/hollow_atom.summon"):
        os.remove(".spatia/logs/hollow_atom.summon")

def test_summoning_flow():
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
        print(res.json())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "summoned"
    
    # 4. Verification
    with sqlite3.connect(TEST_DB) as conn:
        row = conn.execute("SELECT status, content FROM atoms WHERE id='hollow_atom'").fetchone()
        status, content = row[0], row[1]
        
        print(f"Status after summon: {status}")
        # Should be witnessing (2) or Claim (1) or Endorsed (3) depending on timing.
        # Since background task might not have finished, check if it's NOT 0.
        assert status != 0
        assert ";; SUMMONED BY SPATIA" in content
        
    # 5. Check Log
    import time
    # Give a moment for file write if async (it is sync in endpoint)
    assert os.path.exists(".spatia/logs/hollow_atom.summon")
    with open(".spatia/logs/hollow_atom.summon") as f:
        log = f.read()
        print(log)
        assert "Intent:" in log
        assert "/etc/nixos/configuration.nix" in log

def test_summoning_fail_if_not_hollow():
    with sqlite3.connect(TEST_DB) as conn:
        conn.execute("INSERT INTO atoms (id, status, content) VALUES ('filled_atom', 1, 'code')")
        conn.commit()
    
    res = client.post("/api/summon", json={"atom_id": "filled_atom"})
    assert res.status_code == 400
