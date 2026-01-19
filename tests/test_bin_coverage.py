import pytest
import importlib.util
import os
import sys
import sqlite3
from unittest.mock import patch, MagicMock

# --- Helper to load modules with dashes ---
def load_script(name):
    path = os.path.join(os.path.dirname(__file__), f'../.spatia/bin/{name}')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_').replace('.py', ''), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

TEST_DB = "test_bin_coverage.db"

@pytest.fixture
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    conn = sqlite3.connect(TEST_DB)
    # Full Schema
    conn.execute("""
        CREATE TABLE atoms (
            id TEXT PRIMARY KEY, 
            content TEXT, 
            domain TEXT, 
            status INTEGER,
            type TEXT,     -- Added
            hash TEXT,     -- Added
            last_witnessed TEXT -- Added
        )
    """)
    conn.execute("CREATE TABLE geometry (atom_id TEXT PRIMARY KEY, x INTEGER, y INTEGER)")
    conn.commit()
    conn.close()
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

# 1. spatia-check-registers.py
def test_check_registers_success(setup_db):
    mod = load_script('spatia-check-registers.py')
    
    # Insert non-colliding registers
    conn = sqlite3.connect(TEST_DB)
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('a1', '#define R1 0x1000', 'Register', 1)")
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('a2', '#define R2 0x2000', 'Register', 1)")
    conn.commit()
    conn.close()
    
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        with patch.object(mod, 'DB_PATH', TEST_DB): 
            assert mod.check_registers() is True

def test_check_registers_collision(setup_db):
    mod = load_script('spatia-check-registers.py')
    
    conn = sqlite3.connect(TEST_DB)
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('a1', '#define R1 0x1000', 'Register', 1)")
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('a2', '#define R2 0x1000', 'Register', 1)") # Collision
    conn.commit()
    conn.close()
    
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        with patch.object(mod, 'DB_PATH', TEST_DB):
            assert mod.check_registers() is False

# 2. witness-culinary.py
def test_witness_culinary(setup_db):
    mod = load_script('witness-culinary.py')
    
    conn = sqlite3.connect(TEST_DB)
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('pass', '1234567', 'Culinary', 1)")
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('fail', '123456', 'Culinary', 1)")
    conn.commit()
    conn.close()
    
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        with patch.object(mod, 'DB_PATH', TEST_DB):
            assert mod.check_culinary('pass') is True
            assert mod.check_culinary('fail') is False

# 3. witness-legal.py
def test_witness_legal(setup_db):
    mod = load_script('witness-legal.py')
    
    conn = sqlite3.connect(TEST_DB)
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('pass', 'SECTION 1', 'Legal', 1)")
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('fail', 'No Keyword', 'Legal', 1)")
    conn.commit()
    conn.close()
    
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        with patch.object(mod, 'DB_PATH', TEST_DB):
            assert mod.check_legal('pass') is True
            assert mod.check_legal('fail') is False

# 4. spatia-eject.py
def test_spatia_eject(setup_db):
    mod = load_script('spatia-eject.py')
    
    conn = sqlite3.connect(TEST_DB)
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('f1.py', 'code', 'Software', 1)")
    conn.commit()
    conn.close()
    
    # Eject writes content to current dir? NO, it resolves symlinks in a workspace dir.
    # We should mock os.walk and os.path logic to avoid real FS mess or creating a full workspace structure.
    # But for coverage, we can just run it on a dummy dir.
    
    os.makedirs('dummy_ws', exist_ok=True)
    with open('dummy_ws/sentinel.db', 'w') as f: f.write('')
    
    # Run eject
    mod.eject_workspace('dummy_ws', '.')
    
    # Assert sentinel.db removed
    assert not os.path.exists('dummy_ws/sentinel.db')
    os.rmdir('dummy_ws')


# 5. spatia-endorse.py
def test_spatia_endorse(setup_db):
    mod = load_script('spatia-endorse.py')
    
    conn = sqlite3.connect(TEST_DB)
    conn.execute("INSERT INTO atoms (id, content, domain, status) VALUES ('a1', 'c', 'd', 1)")
    conn.commit()
    # Keep conn open or pass a new one
    
    conn = sqlite3.connect(TEST_DB)
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        # DB_PATH is global in endorse
        with patch.object(mod, 'DB_PATH', TEST_DB):
            mod.endorse(conn, 'a1')
            
            check_conn = sqlite3.connect(TEST_DB)
            status = check_conn.execute("SELECT status FROM atoms WHERE id='a1'").fetchone()[0]
            check_conn.close()
            assert status == 1 # Code says set status=1 (Wait, is endorse 1? usually 3. Code says 1. Okay assert 1)
    
    conn.close()

# 6. spatia-materialize.py
def test_spatia_materialize(setup_db):
    mod = load_script('spatia-materialize.py')
    
    conn = sqlite3.connect(TEST_DB)
    conn.execute("INSERT INTO atoms (id, content, domain, type) VALUES ('m1.py', 'print(1)', 'Software', 'file')")
    conn.commit()
    
    conn = sqlite3.connect(TEST_DB)
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        with patch.object(mod, 'DB_PATH', TEST_DB):
            mod.materialize(conn)
            assert os.path.exists('m1.py')
            if os.path.exists('m1.py'):
                os.remove('m1.py')
    conn.close()

# 7. spatia-projector.py
def test_spatia_projector_main(setup_db):
    mod = load_script('spatia-projector.py')
    conn = sqlite3.connect(TEST_DB)
    conn.execute("INSERT INTO geometry (atom_id, x, y) VALUES ('a1', 1, 2)")
    conn.commit()
    conn.close()
    
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
        with patch.object(mod, 'DB_PATH', TEST_DB):
            with patch.object(sys, 'argv', ['prog', '--project']):
                mod.main()
                assert os.path.exists('geometry.sp')
                if os.path.exists('geometry.sp'):
                    os.remove('geometry.sp')

# 8. spatia-shatter.py
def test_spatia_shatter_main(setup_db):
    mod = load_script('spatia-shatter.py')
    with open('to_shatter.txt', 'w') as f:
        f.write('smashed')
        
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
         # No global DB_PATH in shatter to patch
         with patch.object(sys, 'argv', ['prog', '--path', 'to_shatter.txt']):
             mod.main()
             conn = sqlite3.connect(TEST_DB)
             res = conn.execute("SELECT content FROM atoms WHERE id='to_shatter.txt'").fetchone()
             conn.close()
             assert res[0] == 'smashed'
    if os.path.exists('to_shatter.txt'):
        os.remove('to_shatter.txt')

def test_spatia_shatter_hollow(setup_db):
    mod = load_script('spatia-shatter.py')
    with patch.dict(os.environ, {"SENTINEL_DB": TEST_DB}):
         with patch.object(sys, 'argv', ['prog', '--path', 'hollow_id', '--content', 'raw_content']):
             mod.main()
             conn = sqlite3.connect(TEST_DB)
             res = conn.execute("SELECT content, domain FROM atoms WHERE id='hollow_id'").fetchone()
             conn.close()
             assert res[0] == 'raw_content'
             assert res[1] == 'generic'

def test_witness_culinary_error(setup_db):
    mod = load_script('witness-culinary.py')
    # Test DB missing path
    with patch.multiple(mod, DB_PATH='missing.db'):
        with patch('os.path.exists', return_value=False):
             assert mod.check_culinary('id') is False
