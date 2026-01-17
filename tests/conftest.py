import pytest
import shutil
import os
import sqlite3
from fastapi.testclient import TestClient
from backend.main import app, get_db_connection

# Override DB path for tests
TEST_DB_PATH = '.spatia/test_sentinel.db'

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Setup: Create a clean DB or copy schema
    # For now, just ensuring directory exists and it's clean
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # Initialize basic schema
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS atoms (id TEXT PRIMARY KEY, type TEXT, content TEXT, hash TEXT, domain TEXT DEFAULT 'generic', status INTEGER DEFAULT 0, parent_project TEXT, last_witnessed TEXT);")
    cursor.execute("CREATE TABLE IF NOT EXISTS geometry (atom_id TEXT PRIMARY KEY, pane_id TEXT, x INTEGER, y INTEGER);")
    conn.commit()
    conn.close()
    
    yield
    
    # Teardown
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture
def client():
    # Override the dependency
    def override_get_db():
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    app.dependency_overrides[get_db_connection] = override_get_db
    # Note: backend.main.get_db_connection is used inside the routes but currently 
    # the routes call get_db_connection() directly, not as a dependency injection in all cases.
    # Looking at main.py:
    # 
    # def get_db_connection(): ...
    # 
    # @app.post("/api/shatter")
    # async def shatter_atom(request: ShatterRequest):
    #    ...
    #    with get_db_connection() as conn: ...
    #
    # Since get_db_connection is imported/defined globally, we might need to patch it 
    # or modify main.py to allow injection.
    # 
    # For now, let's patch the global variable DB_PATH in main.py if possible, 
    # or just use unittest.mock.patch.
    
    from backend import main
    main.DB_PATH = TEST_DB_PATH
    
    return TestClient(app)
