import requests
import json
import threading
import time
import sys

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

BASE_URL = "http://127.0.0.1:8000"
SSE_URL = f"{BASE_URL}/api/events"
ERROR_URL = f"{BASE_URL}/api/test_error"

error_received = False

def listen_sse():
    global error_received
    print("Connecting to SSE...")
    try:
        response = requests.get(SSE_URL, stream=True)
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    try:
                        data = json.loads(data_str)
                        print(f"Received Event: {data}")
                        if data.get("type") == "error":
                            if "This is a test error for broadcasting" in data.get("message", ""):
                                print(f"{GREEN}SUCCESS: Error event received!{RESET}")
                                error_received = True
                                return # Exit thread
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"SSE Error: {e}")

def trigger_error():
    time.sleep(2) # Wait for SSE to connect
    print("Triggering Error...")
    try:
        resp = requests.get(ERROR_URL)
        print(f"Trigger Response Code: {resp.status_code}") # Should be 500
    except Exception as e:
        print(f"Trigger Exception: {e}")

if __name__ == "__main__":
    t = threading.Thread(target=listen_sse)
    t.start()
    
    trigger_error()
    
    t.join(timeout=5)
    
    if error_received:
        sys.exit(0)
    else:
        print(f"{RED}FAILED: Did not receive error event.{RESET}")
        sys.exit(1)
