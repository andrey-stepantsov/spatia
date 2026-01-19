import os
import shutil
import subprocess
import time
import signal
import sys
import urllib.request
import urllib.error

# Configuration
PORT = 8000
BASE_URL = f"http://localhost:{PORT}"
ROOT_DIR = "/Users/stepants/dev/spatia"
SPATIA_DIR = os.path.join(ROOT_DIR, ".spatia")
WORKSPACES_DIR = os.path.join(ROOT_DIR, "workspaces")
DB_PATH = os.path.join(SPATIA_DIR, "sentinel.db")

def run_command(command, cwd=None, env=None):
    """Run a shell command."""
    print(f"Running: {command}")
    try:
        subprocess.check_call(command, shell=True, cwd=cwd, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        raise

def kill_server():
    """Kill process listening on PORT."""
    print(f"Checking for process on port {PORT}...")
    try:
        # lsof -ti :8000
        pid_bytes = subprocess.check_output(["lsof", "-ti", f":{PORT}"])
        pids = pid_bytes.decode().strip().split('\n')
        for pid in pids:
            if pid:
                print(f"Killing process {pid}")
                os.kill(int(pid), signal.SIGKILL)
        time.sleep(1)
    except subprocess.CalledProcessError:
        print("No process found on port.")
    except Exception as e:
        print(f"Error killing process: {e}")

def reset_data():
    """Delete .spatia metadata and workspaces."""
    print("Resetting data...")
    
    # 1. Remove .spatia/sentinel.db (and symlink)
    if os.path.exists(DB_PATH) or os.path.islink(DB_PATH):
        print(f"Removing {DB_PATH}")
        os.remove(DB_PATH)
        
    # 2. Remove other .spatia artifacts if needed
    for subdir in ["atoms", "geometry", "portals", "logs"]:
        path = os.path.join(SPATIA_DIR, subdir)
        if os.path.exists(path):
            print(f"Cleaning {path}")
            shutil.rmtree(path)
            os.makedirs(path, exist_ok=True)
            
    # 3. Clean workspaces
    if os.path.exists(WORKSPACES_DIR):
        print(f"Cleaning {WORKSPACES_DIR}")
        shutil.rmtree(WORKSPACES_DIR)
    os.makedirs(WORKSPACES_DIR, exist_ok=True)
    
    # 4. Run make setup
    run_command("make setup", cwd=ROOT_DIR)

def start_server():
    """Start the uvicorn server in background."""
    print("Starting backend server...")
    log_file = open(os.path.join(ROOT_DIR, "backend_server.log"), "w")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(PORT)],
        cwd=ROOT_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return process

def wait_for_health():
    """Wait for server to respond."""
    print("Waiting for server health...")
    retries = 30
    for i in range(retries):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/workspaces") as response:
                if response.status == 200:
                    print("Server is up!")
                    return True
        except (urllib.error.URLError, ConnectionResetError):
            time.sleep(1)
            print(".", end="", flush=True)
    print("\nServer failed to start.")
    return False

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-server", action="store_true", help="Do not start the backend server")
    args = parser.parse_args()

    kill_server()
    reset_data()
    
    if not args.no_server:
        server_process = start_server()
        try:
            if wait_for_health():
                print("Environment ready for testing.")
            else:
                print("Failed to start environment.")
                sys.exit(1)
        except KeyboardInterrupt:
            print("Stopping...")
            server_process.terminate()
    else:
        print("Environment reset complete (Server not started).")

if __name__ == "__main__":
    main()
