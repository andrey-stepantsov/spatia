#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = '.spatia/sentinel.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def materialize(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, content FROM atoms WHERE type = 'file'")
    atoms = cursor.fetchall()

    for atom_id, content in atoms:
        # atom_id is the relative path
        if os.path.isabs(atom_id):
            print(f"Warning: Skipping absolute path atom: {atom_id}")
            continue
            
        dir_name = os.path.dirname(atom_id)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        try:
            with open(atom_id, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Materialized: {atom_id}")
        except Exception as e:
            print(f"Error writing {atom_id}: {e}")

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found. Run 'make setup' first.")
        exit(1)
        
    conn = init_db()
    materialize(conn)
    conn.close()
