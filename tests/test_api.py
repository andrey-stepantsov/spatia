import os
import sqlite3
import pytest

def test_read_main(client):
    response = client.get("/api/atoms")
    # Should be 200 even if empty
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_geometry(client, mock_db):
    # Manually insert an atom to test geometry update
    cursor = mock_db.cursor()
    cursor.execute("INSERT INTO atoms (id, type, content) VALUES ('test_atom', 'text', 'hello')")
    mock_db.commit()

    # Update geometry
    payload = [{"atom_id": "test_atom", "x": 100, "y": 200}]
    response = client.post("/api/geometry", json=payload)
    assert response.status_code == 200
    
    # Verify persistence via GET
    response = client.get("/api/atoms")
    atoms = response.json()
    target = next((a for a in atoms if a['id'] == 'test_atom'), None)
    assert target is not None
    assert target['x'] == 100
    assert target['y'] == 200

# NOTE: Testing /api/shatter requires the actual spatia-shatter script to run.
# Since we are in a devbox environment, we could mock the subprocess call, 
# or just ensure the endpoint handles the request structure correctly.
# For this smoke test, let's mock the subprocess for safety/speed.

from unittest.mock import patch, AsyncMock

@patch('backend.main.run_subprocess_async', new_callable=AsyncMock)
def test_shatter_mocked(mock_run, client, mock_db):
    # Mock return value
    mock_run.return_value = "ATOM_ID: new_atom_123"
    
    payload = {"path": "test.txt", "content": "some content"}
    response = client.post("/api/shatter", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"atom_id": "new_atom_123"}
    
    # Verify geometry initialized to 0,0
    cursor = mock_db.cursor()
    cursor.execute("SELECT x, y FROM geometry WHERE atom_id = 'new_atom_123'")
    row = cursor.fetchone()
    
    assert row is not None
    assert row[0] == 0
    assert row[1] == 0
