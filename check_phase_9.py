import sqlite3
import os
import subprocess

def check_phase_9():
    results = []
    
    # 1. Check Sentinel DB Schema
    try:
        conn = sqlite3.connect('.spatia/sentinel.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(atoms)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'domain' in columns and 'status' in columns:
            results.append("✅ Sentinel DB: Schema updated with Domain/Status.")
        else:
            results.append("❌ Sentinel DB: Missing Domain or Status columns.")
    except Exception as e:
        results.append(f"❌ Sentinel DB: Could not connect ({e})")

    # 2. Check Real-Time Bridge (SSE)
    if os.path.exists('backend/main.py'):
        with open('backend/main.py', 'r') as f:
            content = f.read()
            if 'StreamingResponse' in content and 'text/event-stream' in content:
                results.append("✅ Backend: SSE bridge detected.")
            else:
                results.append("❌ Backend: SSE logic missing.")

    # 3. Check Hardware Domain Logic
    if os.path.exists('.spatia/bin/spatia-shatter.py'):
        with open('.spatia/bin/spatia-shatter.py', 'r') as f:
            if 'Register' in f.read():
                results.append("✅ Shatterer: Register Domain logic found.")
            else:
                results.append("❌ Shatterer: Hardware Domain logic missing.")

    # 4. Check Fossil Integrity (Ghost Mode)
    try:
        cursor.execute("SELECT COUNT(*) FROM atoms WHERE status = 4")
        fossils = cursor.fetchone()[0]
        results.append(f"✅ USG State: Found {fossils} Fossil atoms in temporal storage.")
    except:
        results.append("❌ USG State: Fossil query failed.")

    print("\n--- Spatia Phase 10 Readiness Report ---")
    for r in results:
        print(r)
    print("-----------------------------------------\n")

if __name__ == "__main__":
    check_phase_9()
