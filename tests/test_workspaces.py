
import os
import shutil
import pytest
from fastapi.testclient import TestClient
from backend.main import app
import time

client = TestClient(app)

@pytest.fixture
def clean_workspaces():
    # Setup
    os.makedirs("workspaces", exist_ok=True)
    yield
    # Teardown: clean up test workspaces
    for ws in ["test_ws_1", "test_ws_clone", "test_ws_eject"]:
        path = os.path.join("workspaces", ws)
        if os.path.isdir(path):
            shutil.rmtree(path)
        # Also check if ejected (standalone)
        if os.path.isdir(path):
            shutil.rmtree(path)
            
def test_create_workspace(clean_workspaces):
    response = client.post("/api/workspaces", json={"name": "test_ws_1"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["workspace"] == "test_ws_1"
    
    assert os.path.exists("workspaces/test_ws_1/sentinel.db")
    assert os.path.exists("workspaces/test_ws_1/geometry.sp")

def test_snapshot_workspace(clean_workspaces):
    # Create first
    client.post("/api/workspaces", json={"name": "test_ws_1"})
    
    response = client.post("/api/workspaces/test_ws_1/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "snapshotted"
    
    # Check for snapshot file
    ws_dir = "workspaces/test_ws_1"
    files = os.listdir(ws_dir)
    snaps = [f for f in files if f.startswith("sentinel.snap.")]
    assert len(snaps) == 1

def test_clone_workspace(clean_workspaces):
    # Create first
    client.post("/api/workspaces", json={"name": "test_ws_1"})
    
    # 1. Test Auto-Naming
    response = client.post("/api/workspaces/test_ws_1/clone")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cloned"
    assert data["target"] == "test_ws_1-copy"
    assert os.path.exists("workspaces/test_ws_1-copy/sentinel.db")

    # 2. Test Custom Naming
    response = client.post("/api/workspaces/test_ws_1/clone", json={"new_name": "custom_clone_name"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cloned"
    assert data["target"] == "custom_clone_name"
    assert os.path.exists("workspaces/custom_clone_name/sentinel.db")
    
    # 3. Test Custom Naming Collision
    response = client.post("/api/workspaces/test_ws_1/clone", json={"new_name": "custom_clone_name"})
    assert response.status_code == 409
    
    # Clean up clones
    for d in ["workspaces/test_ws_1-copy", "workspaces/custom_clone_name"]:
        if os.path.isdir(d):
            shutil.rmtree(d)

def test_eject_workspace(clean_workspaces):
    # Create first
    client.post("/api/workspaces", json={"name": "test_ws_eject"})
    
    # Add a dummy symlink to test resolution
    ws_dir = "workspaces/test_ws_eject"
    dummy_target = "dummy_target.txt"
    with open(dummy_target, "w") as f:
        f.write("content")
    
    link_path = os.path.join(ws_dir, "my_link.txt")
    # Need absolute path for symlink if not careful, but os.symlink src is first
    # os.symlink(src, dst)
    # relative src is relative to dst directory logic? No, relative to CWD if running script?
    # No, os.symlink logic.
    os.symlink(os.path.abspath(dummy_target), link_path)
    
    # Run Eject
    response = client.post("/api/workspaces/test_ws_eject/eject")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ejected"
    
    # Verify Metadata Gone
    assert not os.path.exists(os.path.join(ws_dir, "sentinel.db"))
    assert not os.path.exists(os.path.join(ws_dir, "geometry.sp"))
    
    # Verify Symlink Replaced
    assert os.path.exists(link_path)
    assert not os.path.islink(link_path)
    with open(link_path, "r") as f:
        assert f.read() == "content"
        
    # Cleanup
    os.remove(dummy_target)
    shutil.rmtree("workspaces/test_ws_eject")
