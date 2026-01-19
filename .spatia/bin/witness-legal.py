#!/usr/bin/env python3
import sys
import os
import sqlite3

DB_PATH = os.environ.get('SENTINEL_DB', '.spatia/sentinel.db')

def check_legal(atom_id):
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT content FROM atoms WHERE id = ?", (atom_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print(f"Error: Atom {atom_id} not found.")
        return False
        
    content = row['content']
    
    print(f"Legal Witness: Checking atom {atom_id}")
    
    # Simple check: Must contain at least one "SECTION" (case-insensitive)
    if "SECTION" in content.upper():
        print("Legal Check Passed: Found 'SECTION' clause.")
        return True
    else:
        print("Legal Check Failed: Missing 'SECTION' clause.")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: witness-legal.py <atom_id>")
        sys.exit(1)
        
    atom_id = sys.argv[1]
    if not check_legal(atom_id):
        sys.exit(1)
    sys.exit(0)
