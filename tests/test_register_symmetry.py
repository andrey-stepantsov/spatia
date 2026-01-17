import pytest
import sqlite3
import os
import subprocess
import asyncio

# Path to the script we are testing
CHECK_SCRIPT = ".spatia/bin/spatia-check-registers.py"

@pytest.fixture
def temp_db(tmp_path):
    """Creates a temporary Sentinel DB with schematic"""
    db_file = tmp_path / "sentinel.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE atoms (
            id TEXT PRIMARY KEY,
            type TEXT,
            content TEXT,
            hash TEXT,
            domain TEXT DEFAULT 'generic',
            status INTEGER DEFAULT 0,
            parent_project TEXT,
            last_witnessed TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db_file

def insert_atom(db_path, atom_id, content, domain="Register", status=1):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO atoms (id, content, domain, status)
        VALUES (?, ?, ?, ?)
    """, (atom_id, content, domain, status))
    conn.commit()
    conn.close()

def run_check_script(db_path):
    env = os.environ.copy()
    env["SENTINEL_DB"] = str(db_path)
    
    result = subprocess.run(
        [CHECK_SCRIPT],
        env=env,
        capture_output=True,
        text=True
    )
    return result

def test_register_symmetry_success(temp_db):
    # No overlapping registers
    insert_atom(temp_db, "a.h", "#define REG_A 0x1000")
    insert_atom(temp_db, "b.h", "#define REG_B 0x2000")
    
    result = run_check_script(temp_db)
    assert result.returncode == 0
    assert "Symmetry Check Passed" in result.stdout

def test_register_symmetry_failure(temp_db):
    # Overlapping registers
    insert_atom(temp_db, "a.h", "#define REG_X 0x1000")
    insert_atom(temp_db, "b.h", "#define REG_Y 0x1000") # Collision
    
    result = run_check_script(temp_db)
    assert result.returncode == 1
    assert "Symmetry Check Failed" in result.stdout
    assert "Collision Detected" in result.stdout

def test_ignore_fossil_status(temp_db):
    # Collision but one is a fossil (Status 4) -> Should Pass (as per script logic update)
    # Wait, did we exclude status 4?
    # Script: SELECT ... WHERE domain = 'Register' AND status != 4
    
    insert_atom(temp_db, "active.h", "#define REG_X 0x1000", status=1)
    insert_atom(temp_db, "old.h", "#define REG_X 0x1000", status=4) # Fossil
    
    result = run_check_script(temp_db)
    assert result.returncode == 0
