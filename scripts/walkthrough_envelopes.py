
import requests
import time
import sys
import json

BASE_URL = "http://localhost:8000"

def log(msg, step=None):
    prefix = f"[Step {step}] " if step else "[INFO] "
    print(f"{prefix}{msg}")

def check(response, expected_status=200, context=""):
    if response.status_code != expected_status:
        print(f"[FAIL] {context} - Expected {expected_status}, got {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
    else:
        print(f"[PASS] {context}")

def run_walkthrough():
    log("Starting Phase 12 Walkthrough: Spatial Envelopes")
    
    # 1. Create Workspace
    ws_name = f"walkthrough-{int(time.time())}"
    log(f"Creating Workspace: {ws_name}", 1)
    
    # Switch/Init Workspace logic manually? 
    # The API has /api/workspaces POST -> creates and inits DB
    # Then /api/workspace/switch -> switches context
    
    # Create
    res = requests.post(f"{BASE_URL}/api/workspaces", json={"name": ws_name})
    check(res, 200, "Create Workspace")
    
    # Switch
    res = requests.post(f"{BASE_URL}/api/workspace/switch", json={"name": ws_name})
    check(res, 200, "Switch to Workspace")
    
    # 2. Create Envelope
    log("Creating Envelope 'System Zone' (Domain: system)", 2)
    env_id = "env-system-01"
    res = requests.post(f"{BASE_URL}/api/envelopes", json={
        "id": env_id,
        "domain": "system",
        "x": 100, "y": 100, "w": 400, "h": 300
    })
    check(res, 200, "Create Envelope")
    
    # Verify it exists
    res = requests.get(f"{BASE_URL}/api/envelopes")
    check(res, 200, "Fetch Envelopes")
    envs = res.json()
    assert len(envs) == 1, f"Expected 1 envelope, got {len(envs)}"
    assert envs[0]['id'] == env_id
    log("Envelope verification successful")

    # 3. Create Atom (Simulated)
    # We can't easily create a file via API unless we use 'shatter' or specific 'summon' hacks?
    # Or just insert directly?
    # Actually, we can just assume existing atoms or use the 'shatter' endpoint if we have a file.
    # Let's simple check backend Envelope logic.
    
    # 4. Resize Envelope (Update)
    log("Resizing Envelope", 3)
    res = requests.put(f"{BASE_URL}/api/envelopes/{env_id}", json={
        "w": 500,
        "h": 400
    })
    check(res, 200, "Update Envelope")
    
    # Verify update
    res = requests.get(f"{BASE_URL}/api/envelopes")
    updated_env = res.json()[0]
    assert updated_env['w'] == 500
    log("Resize verification successful")
    
    # 5. Domain Update
    log("Updating Domain to 'security'", 4)
    res = requests.put(f"{BASE_URL}/api/envelopes/{env_id}", json={"domain": "security"})
    check(res, 200, "Update Domain")
    
    res = requests.get(f"{BASE_URL}/api/envelopes")
    assert res.json()[0]['domain'] == 'security'
    log("Domain update verification successful")

    # 6. Delete Envelope
    log("Deleting Envelope", 5)
    res = requests.delete(f"{BASE_URL}/api/envelopes/{env_id}")
    check(res, 200, "Delete Envelope")
    
    res = requests.get(f"{BASE_URL}/api/envelopes")
    assert len(res.json()) == 0
    log("Delete verification successful")
    
    # 7. Cleanup (Switch back to default)
    log("Cleaning up...", 6)
    requests.post(f"{BASE_URL}/api/workspace/switch", json={"name": "default"})
    
    # Optionally Eject/Delete the test workspace?
    # requests.post(f"{BASE_URL}/api/workspaces/{ws_name}/eject")
    
    log("Walkthrough Complete - ALL SYSTEMS GO")

if __name__ == "__main__":
    try:
        run_walkthrough()
    except Exception as e:
        print(f"\n[ERROR] Walkthrough failed: {e}")
        sys.exit(1)
