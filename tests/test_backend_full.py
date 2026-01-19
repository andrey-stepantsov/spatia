import unittest
import requests
import time
import os
import json

BASE_URL = "http://localhost:8000/api"
ROOT_DIR = "/Users/stepants/dev/spatia"

class TestSpatiaBackend(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Cleanup potential dirty state from previous runs
        import shutil
        for ws in ["test-ws-automation", "test-ws-clone"]:
            p = os.path.join(ROOT_DIR, "workspaces", ws)
            if os.path.exists(p):
                shutil.rmtree(p)
                
        # Ensure server is reachable
        try:
            requests.get(f"{BASE_URL}/workspaces", timeout=5)
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Backend server is not running. Please run scripts/reset_env.py first.")

    def test_01_workspaces_initial(self):
        """Test initial workspaces listing."""
        r = requests.get(f"{BASE_URL}/workspaces")
        self.assertEqual(r.status_code, 200)
        workspaces = r.json()
        self.assertIsInstance(workspaces, list)
        # self.assertIn("default", workspaces) # Reset environment might not have default

    def test_02_create_workspace(self):
        """Create a new workspace."""
        name = "test-ws-automation"
        r = requests.post(f"{BASE_URL}/workspaces", json={"name": name})
        self.assertEqual(r.status_code, 200)
        
        # Verify it lists
        r = requests.get(f"{BASE_URL}/workspaces")
        self.assertIn(name, r.json())

    def test_03_switch_workspace(self):
        """Switch to the new workspace."""
        name = "test-ws-automation"
        r = requests.post(f"{BASE_URL}/workspace/switch", json={"name": name})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["workspace"], name)
        
        # Verify atoms is empty (new db)
        r = requests.get(f"{BASE_URL}/atoms")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 0)

    def test_04_shatter_atom(self):
        """Shatter a file to create an atom."""
        # Create a test file first
        test_file = "atoms/test_backend_atom.md"
        abs_test_file = os.path.join(ROOT_DIR, test_file)
        os.makedirs(os.path.dirname(abs_test_file), exist_ok=True)
        with open(abs_test_file, "w") as f:
            f.write("# Backend Test Atom")
            
        # Call shatter
        r = requests.post(f"{BASE_URL}/shatter", json={"path": test_file, "content": "# Backend Test Atom"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["atom_id"], test_file)
        
        # Verify in DB
        r = requests.get(f"{BASE_URL}/atoms")
        atoms = r.json()
        self.assertEqual(len(atoms), 1)
        self.assertEqual(atoms[0]["id"], test_file)
        # Status might be 1 (Claim)
        
    def test_05_update_geometry(self):
        """Test geometry update."""
        atom_id = "atoms/test_backend_atom.md"
        r = requests.post(f"{BASE_URL}/geometry", json=[{"atom_id": atom_id, "x": 100, "y": 200}])
        self.assertEqual(r.status_code, 200)
        
        # Verify
        r = requests.get(f"{BASE_URL}/atoms")
        atom = next(a for a in r.json() if a["id"] == atom_id)
        self.assertEqual(atom["x"], 100)
        self.assertEqual(atom["y"], 200)

    def test_07_witness(self):
        """Witness the atom."""
        atom_id = "atoms/test_backend_atom.md"
        
        # Trigger witness
        r = requests.post(f"{BASE_URL}/witness", json={"atom_id": atom_id})
        self.assertEqual(r.status_code, 200)
        
        # Wait for background process
        max_retries = 20
        final_status = None
        for _ in range(max_retries):
            time.sleep(0.5)
            r = requests.get(f"{BASE_URL}/atoms")
            atom = next(a for a in r.json() if a["id"] == atom_id)
            final_status = atom["status"]
            if final_status in [3, 1] and final_status != 2: # 2 is witnessing
                break
        
        # We assume it finishes. Logic: 3 if exit 0, else 1.
        self.assertIn(final_status, [1, 3])

    def test_08_threads(self):
        """Test threads creation."""
        r = requests.post(f"{BASE_URL}/threads", json={"source": "a", "target": "b"})
        self.assertEqual(r.status_code, 200)
        
        r = requests.get(f"{BASE_URL}/threads")
        threads = r.json()
        self.assertTrue(any(t["source"] == "a" and t["target"] == "b" for t in threads))

    def test_09_clone_and_eject(self):
        """Clone current workspace and then eject/delete it."""
        current_ws = "test-ws-automation"
        clone_name = "test-ws-clone"
        
        # Clone
        r = requests.post(f"{BASE_URL}/workspaces/{current_ws}/clone", json={"new_name": clone_name})
        self.assertEqual(r.status_code, 200)
        
        # Verify existence
        r = requests.get(f"{BASE_URL}/workspaces")
        self.assertIn(clone_name, r.json())
        
        # Eject
        r = requests.post(f"{BASE_URL}/workspaces/{clone_name}/eject")
        self.assertEqual(r.status_code, 200)
        
        # Check list again (should be gone from tracked workspaces)
        r = requests.get(f"{BASE_URL}/workspaces")
        self.assertNotIn(clone_name, r.json())

if __name__ == "__main__":
    unittest.main()
