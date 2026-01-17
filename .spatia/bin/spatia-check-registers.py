#!/usr/bin/env python3
import sqlite3
import re
import sys
import os

DB_PATH = os.environ.get('SENTINEL_DB', '.spatia/sentinel.db')

def check_registers():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Select all Register atoms
    cursor.execute("SELECT id, content FROM atoms WHERE domain = 'Register' AND status != 4")
    atoms = cursor.fetchall()
    
    # Format: address -> atom_id
    address_map = {}
    
    failure = False
    
    for atom in atoms:
        atom_id = atom['id']
        content = atom['content']
        
        # Regex to find hex literals: #define ... 0x...
        # Simple heuristic: find all hex numbers
        # Refined: #define\s+\w+\s+(0x[0-9A-Fa-f]+)
        matches = re.findall(r'#define\s+\w+\s+(0x[0-9A-Fa-f]+)', content)
        
        for addr_str in matches:
            try:
                addr = int(addr_str, 16)
                if addr in address_map:
                    print(f"Collision Detected! Address {addr_str} in {atom_id} overlaps with {address_map[addr]}")
                    failure = True
                else:
                    address_map[addr] = atom_id
            except ValueError:
                continue
                
    conn.close()
    
    if failure:
        print("Symmetry Check Failed: Overlapping Registers detected.")
        return False
    else:
        print(f"Symmetry Check Passed: {len(address_map)} unique registers verified.")
        return True

if __name__ == '__main__':
    if not check_registers():
        sys.exit(1)
    sys.exit(0)
