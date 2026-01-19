
import os
import subprocess
import time
import signal
import glob
import sys
import shutil

# Configuration
PROJECT_ROOT = "/Users/stepants/dev/spatia"
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv/bin/python3")
RESET_SCRIPT = os.path.join(PROJECT_ROOT, "scripts/reset_env.py")

def log(msg):
    print(f"\n[ISOLATED RUNNER] {msg}", flush=True)

def run_cmd(cmd, cwd=PROJECT_ROOT, background=False, env=None):
    if background:
        return subprocess.Popen(cmd, shell=True, cwd=cwd, executable="/bin/bash", env=env)
    return subprocess.run(cmd, shell=True, cwd=cwd, executable="/bin/bash", check=False, env=env)

def kill_port(port):
    try:
        # Surgical kill of port owners
        pid = subprocess.check_output(f"lsof -ti :{port}", shell=True).decode().strip()
        if pid:
            log(f"Killing process {pid} on port {port}")
            subprocess.run(f"kill -9 {pid}", shell=True)
    except subprocess.CalledProcessError:
        pass

def cleanup():
    log("Cleaning up environment...")
    kill_port(8000)


def reset_db():
    log("Resetting Database...")
    subprocess.run([VENV_PYTHON, RESET_SCRIPT, "--no-server"], cwd=PROJECT_ROOT, check=True)

def start_frontend():
    log("Starting Frontend...")
    cmd = "npm run dev -- --port 5173"
    # We don't need to wait for specific health check usually as Vite is fast, but let's be safe
    process = subprocess.Popen(cmd.split(), cwd=FRONTEND_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2) # Give Vite a moment
    return process

def start_backend():
    log("Starting Backend...")
    # Start uvicorn in background
    cmd = f"{VENV_PYTHON} -m uvicorn backend.main:app --port 8000"
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    process = subprocess.Popen(cmd.split(), cwd=PROJECT_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for health
    for _ in range(20):
        try:
            import urllib.request
            if urllib.request.urlopen("http://localhost:8000/api/health").getcode() == 200:
                log("Backend STARTED")
                return process
        except:
            time.sleep(1)
            print(".", end="", flush=True)
    
    log("Backend FAILED to start")
    process.kill()
    sys.exit(1)

def main():
    # 1. Get list of tests
    tests = glob.glob(os.path.join(FRONTEND_DIR, "e2e/*.spec.js"))
    tests.sort()
    
    results = {}
    
    for test_path in tests:
        test_name = os.path.basename(test_path)
        log(f"=== RUNNING: {test_name} ===")
        
        # A. Cleanup & Reset
        kill_port(8000)
        reset_db()
        
        # B. Start Services
        backend_proc = start_backend()
        frontend_proc = start_frontend()
        
        # C. Run Playwright Test
        # We disable the webServer in config by setting an env var if we modify config, 
        # or we rely on 'reuseExistingServer: true' in config which we know checks port 8000.
        # Since we just started port 8000, Playwright should use it.
        env = os.environ.copy()
        env["CI"] = "1" # Force forbidOnly behavior if needed
        env["SKIP_WEBSERVER"] = "1" # Prevent Playwright from trying to start backend
        
        cmd = f"npx playwright test {os.path.basename(test_path)} --reporter=line"
        log(f"Exec: {cmd}")
        
        start_time = time.time()
        ret = run_cmd(cmd, cwd=FRONTEND_DIR, env=env)
        duration = time.time() - start_time
        
        # D. Record Result
        if ret.returncode == 0:
            results[test_name] = ("PASS", duration)
            log(f"PASS: {test_name}")
        else:
            results[test_name] = ("FAIL", duration)
            log(f"FAIL: {test_name}")
            
        # E. Teardown
        backend_proc.kill()
        frontend_proc.kill()
        
    # Summary
    log("\n=== TEST SUMMARY ===")
    failed = False
    for name, (status, dur) in results.items():
        print(f"{status.ljust(5)} {name.ljust(30)} ({dur:.2f}s)")
        if status == "FAIL": failed = True
        
    if failed:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
