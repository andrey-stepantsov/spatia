import pytest
from unittest.mock import patch, AsyncMock

def test_revive_flow(client, mock_db):
    cursor = mock_db.cursor()
    
    # 1. Setup: Create an Active Atom (Version 2) and a Fossil (Version 1)
    # Active
    cursor.execute("""
        INSERT INTO atoms (id, type, content, hash, status, last_witnessed)
        VALUES ('test.txt', 'file', 'Version 2', 'hash_v2', 1, '2026-01-01T12:00:00')
    """)
    # Fossil
    fossil_id = "test.txt@2026-01-01T10:00:00"
    cursor.execute("""
        INSERT INTO atoms (id, type, content, hash, status, last_witnessed)
        VALUES (?, 'file', 'Version 1', 'hash_v1', 4, '2026-01-01T10:00:00')
    """, (fossil_id,))
    
    # Geometry for Active (should be copied to new fossil)
    cursor.execute("INSERT INTO geometry (atom_id, x, y) VALUES ('test.txt', 10, 20)")
    mock_db.commit()

    # 2. Call Revive
    with patch('backend.main.run_subprocess_async', new_callable=AsyncMock) as mock_run:
        response = client.post("/api/revive", json={"fossil_id": fossil_id})
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'revived'
        assert data['atom_id'] == 'test.txt'
        
        # Verify materialization trigger
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert '.spatia/bin/spatia-materialize.py' in args[0]

    # 3. Verify DB State flow
    cursor.execute("SELECT content, status, hash FROM atoms WHERE id = 'test.txt'")
    current = cursor.fetchone()
    # Content should be Version 1 (from fossil)
    assert current['content'] == 'Version 1'
    # Status should be 1 (Claim)
    assert current['status'] == 1
    assert current['hash'] == 'hash_v1'

    # 4. Verify Old Active (Version 2) is now a Fossil
    # ID should be test.txt@{timestamp}
    cursor.execute("SELECT id, content, status FROM atoms WHERE id LIKE 'test.txt@%' AND content = 'Version 2'")
    new_fossil = cursor.fetchone()
    assert new_fossil is not None
    assert new_fossil['status'] == 4
    
    # 5. Verify Geometry Copied to New Fossil
    cursor.execute("SELECT x, y FROM geometry WHERE atom_id = ?", (new_fossil['id'],))
    geo = cursor.fetchone()
    assert geo is not None
    assert geo['x'] == 10
    assert geo['y'] == 20
