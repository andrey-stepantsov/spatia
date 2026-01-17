import pytest
import sqlite3
import unittest.mock
from fastapi.testclient import TestClient
from backend.main import app, get_db_connection

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
def mock_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Create schema similar to sentinel.db
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE atoms (id TEXT PRIMARY KEY, type TEXT, status INTEGER DEFAULT 1, content TEXT, hash TEXT, last_witnessed TEXT)")
    cursor.execute("CREATE TABLE geometry (atom_id TEXT PRIMARY KEY, x INTEGER, y INTEGER)")
    conn.commit()
    return conn

@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db_connection] = lambda: mock_db
    # Also patch the direct function call since main.py calls it directly
    with unittest.mock.patch('backend.main.get_db_connection', return_value=mock_db):
        yield TestClient(app)
    app.dependency_overrides.clear()
