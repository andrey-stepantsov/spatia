#!/usr/bin/env python3
import argparse
import sqlite3
import re
import os
import sys

# Define color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'

DB_PATH = os.environ.get('SENTINEL_DB', '.spatia/sentinel.db')
PROJECT_FILE = 'geometry.sp'

def get_db():
    if not os.path.exists(DB_PATH):
        print(f"{RED}Error: Database not found at {DB_PATH}{RESET}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def project():
    print(f"{BLUE}Projecting geometry to {PROJECT_FILE}...{RESET}")
    conn = get_db()
    cursor = conn.cursor()
    
    # Fetch Geometry
    cursor.execute("SELECT atom_id, x, y FROM geometry")
    anchors = cursor.fetchall()
    
    # Fetch Threads - check if table exists first (graceful degradation)
    threads = []
    try:
        cursor.execute("SELECT source_id, target_id FROM threads")
        threads = cursor.fetchall()
    except sqlite3.OperationalError:
        print(f"{RED}Warning: 'threads' table not found. Skipping threads projection.{RESET}")

    conn.close()
    
    with open(PROJECT_FILE, 'w') as f:
        # Write Anchors
        for row in anchors:
            # (anchor :ID {x y})
            f.write(f"(anchor :{row['atom_id']} {{x {row['x']} y {row['y']}}})\n")
        
        # Write Threads
        for row in threads:
            # (thread :FROM :TO)
            f.write(f"(thread :{row['source_id']} :{row['target_id']})\n")
            
    print(f"{GREEN}Successfully projected {len(anchors)} anchors and {len(threads)} threads.{RESET}")

def shatter():
    if not os.path.exists(PROJECT_FILE):
        print(f"{RED}Error: {PROJECT_FILE} not found.{RESET}")
        sys.exit(1)
        
    print(f"{BLUE}Shattering {PROJECT_FILE} back into Sentinel DB...{RESET}")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Regex patterns
    # (anchor :ID {x X y Y}) - Flexible whitespace
    anchor_pattern = re.compile(r"\(anchor\s+:([a-zA-Z0-9_\-\.]+)\s+\{x\s+(\d+)\s+y\s+(\d+)\}\)")
    # (thread :FROM :TO)
    thread_pattern = re.compile(r"\(thread\s+:([a-zA-Z0-9_\-\.]+)\s+:([a-zA-Z0-9_\-\.]+)\)")
    
    anchors_count = 0
    threads_count = 0
    
    with open(PROJECT_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'): continue # Skip empty or comments
            
            # Try anchor
            m_anchor = anchor_pattern.match(line)
            if m_anchor:
                atom_id, x, y = m_anchor.groups()
                cursor.execute("""
                    INSERT INTO geometry (atom_id, x, y) VALUES (?, ?, ?)
                    ON CONFLICT(atom_id) DO UPDATE SET x=excluded.x, y=excluded.y
                """, (atom_id, int(x), int(y)))
                anchors_count += 1
                continue
                
            # Try thread
            m_thread = thread_pattern.match(line)
            if m_thread:
                source, target = m_thread.groups()
                # Ensure threads table exists
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO threads (source_id, target_id) VALUES (?, ?)
                    """, (source, target))
                    threads_count += 1
                except sqlite3.OperationalError:
                     print(f"{RED}Warning: 'threads' table missing. Skipping thread {source}->{target}.{RESET}")
                continue
    
    conn.commit()
    conn.close()
    print(f"{GREEN}Successfully shattered {anchors_count} anchors and {threads_count} threads.{RESET}")

def main():
    parser = argparse.ArgumentParser(description="Spatia Projector: Serialize/Deserialize Geometry")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project', action='store_true', help="Serialize DB to geometry.sp")
    group.add_argument('--shatter', action='store_true', help="Deserialize geometry.sp to DB")
    
    args = parser.parse_args()
    
    if args.project:
        project()
    elif args.shatter:
        shatter()

if __name__ == "__main__":
    main()
