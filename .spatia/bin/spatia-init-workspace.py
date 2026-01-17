#!/usr/bin/env python3
import os
import sys
import sqlite3
import argparse

def init_workspace(name, workspaces_dir="workspaces"):
    target_dir = os.path.join(workspaces_dir, name)
    print(f"Initializing workspace '{name}' in {target_dir}...")
    
    if os.path.exists(target_dir):
        print(f"Warning: Directory {target_dir} already exists.")
    else:
        os.makedirs(target_dir)
        
    db_path = os.path.join(target_dir, "sentinel.db")
    geo_path = os.path.join(target_dir, "geometry.sp")
    
    # Touch geometry.sp
    if not os.path.exists(geo_path):
        with open(geo_path, 'w') as f:
            f.write("; Spatia Geometry Projection\n")
            
    # Init DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Schema matches backend/main.py lifespan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atoms (
            id TEXT PRIMARY KEY,
            type TEXT,
            domain TEXT,
            content TEXT,
            status INTEGER DEFAULT 0,
            hash TEXT,
            last_witnessed TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            source_id TEXT,
            target_id TEXT,
            PRIMARY KEY (source_id, target_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            atom_id TEXT,
            path TEXT,
            description TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS envelopes (
            id TEXT PRIMARY KEY,
            domain TEXT,
            x INTEGER,
            y INTEGER,
            w INTEGER,
            h INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geometry (
            atom_id TEXT PRIMARY KEY,
            x INTEGER,
            y INTEGER
        )
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Workspace '{name}' sentinel.db initialized.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize a new Spatia workspace")
    parser.add_argument("name", help="Name of the workspace")
    args = parser.parse_args()
    
    init_workspace(args.name)
