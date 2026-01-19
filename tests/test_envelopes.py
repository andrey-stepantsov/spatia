
import pytest

def test_create_envelope(client):
    resp = client.post("/api/envelopes", json={
        "id": "env-1",
        "domain": "system",
        "x": 100,
        "y": 100,
        "w": 300,
        "h": 200
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    
    # Verify persistence
    resp = client.get("/api/envelopes")
    envs = resp.json()
    assert len(envs) == 1
    assert envs[0]["id"] == "env-1"
    assert envs[0]["domain"] == "system"

def test_update_envelope(client):
    # Setup
    client.post("/api/envelopes", json={
        "id": "env-2",
        "x": 0, "y": 0, "w": 100, "h": 100
    })
    
    # Update
    resp = client.put("/api/envelopes/env-2", json={
        "x": 50,
        "domain": "security"
    })
    assert resp.status_code == 200
    
    # Verify
    resp = client.get("/api/envelopes")
    # Note: client fixture resets DB per test function? 
    # Usually mock_db in conftest is 'function' scoped by default.
    # line 11: @pytest.fixture (default scope=function)
    # So we only see env-2 if reset. If it's env-1 from prev test, it would fail.
    # Assuming fresh DB. 
    # BUT wait, the `mock_db` creates connection once per test.
    
    envs = resp.json()
    assert len(envs) == 1
    env = envs[0]
    assert env["id"] == "env-2"
    assert env["x"] == 50
    assert env["y"] == 0 # Unchanged
    assert env["domain"] == "security"

def test_delete_envelope(client):
    client.post("/api/envelopes", json={"id": "env-3", "x": 0, "y": 0, "w": 10, "h": 10})
    
    resp = client.delete("/api/envelopes/env-3")
    assert resp.status_code == 200
    
    resp = client.get("/api/envelopes")
    assert len(resp.json()) == 0

def test_create_duplicate(client):
    # Create first
    client.post("/api/envelopes", json={"id": "env-dup", "x": 0, "y": 0, "w": 10, "h": 10})
    
    # Create duplicate
    resp = client.post("/api/envelopes", json={"id": "env-dup", "x": 10, "y": 10, "w": 10, "h": 10})
    assert resp.status_code == 409
    data = resp.json()
    # Schema matches http_exception_handler
    assert data["status"] == "error"
    assert data["error"]["message"] == "Envelope ID already exists"

def test_update_all_fields_and_empty(client):
    client.post("/api/envelopes", json={"id": "env-update", "x": 0, "y": 0, "w": 10, "h": 10})
    
    # Partial updates
    resp = client.put("/api/envelopes/env-update", json={"y": 50})
    assert resp.status_code == 200
    assert resp.json()["status"] == "updated"
    
    resp = client.put("/api/envelopes/env-update", json={"w": 100})
    assert resp.status_code == 200
    
    resp = client.put("/api/envelopes/env-update", json={"h": 200})
    assert resp.status_code == 200
    
    # Empty update
    resp = client.put("/api/envelopes/env-update", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_change"
    
    # Verify final state
    resp = client.get("/api/envelopes")
    env = next(e for e in resp.json() if e["id"] == "env-update")
    assert env["y"] == 50
    assert env["w"] == 100
    assert env["h"] == 200
    assert env["x"] == 0 # Original

def test_delete_not_found(client):
    resp = client.delete("/api/envelopes/env-non-existent")
    assert resp.status_code == 404
