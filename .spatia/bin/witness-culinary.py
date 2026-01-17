#!/usr/bin/env python3
import sqlite3
import sys
import os

DB_PATH = os.environ.get('SENTINEL_DB', '.spatia/sentinel.db')

def check_culinary(atom_id):
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
    length = len(content)
    
    print(f"Culinary Witness: Checking atom {atom_id}")
    print(f"Content length: {length}")
    
    if length % 7 == 0:
        print("Math Check Passed: Length is divisible by 7.")
        return True
    else:
        print(f"Math Check Failed: Length {length} is not divisible by 7.")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: witness-culinary.py <atom_id>")
        sys.exit(1)
        
    atom_id = sys.argv[1]
    if not check_culinary(atom_id):
        sys.exit(1)
    sys.exit(0)
