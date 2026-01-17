#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import datetime

DB_PATH = '.spatia/sentinel.db'
IGNORE_DIRS = {'.git', '.spatia', '.agent', '.devbox', '__pycache__'}
IGNORE_FILES = {'.DS_Store'}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def calculate_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


import re

def detect_domain(filename, content):
    if filename.endswith('.h'):
        # Look for hex literals (e.g., 0x1234)
        if re.search(r'0x[0-9A-Fa-f]+', content):
            return 'Register'
    return 'generic'

def shatter(conn):
    cursor = conn.cursor()
    project_root = os.getcwd()

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file in IGNORE_FILES:
                continue
                
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, project_root)
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                print(f"Skipping binary or non-utf8 file: {rel_path}")
                continue
            except Exception as e:
                print(f"Error reading {rel_path}: {e}")
                continue

            file_hash = calculate_hash(content)
            timestamp = datetime.datetime.now().isoformat()
            
            domain = detect_domain(file, content)
            
            query = """
                INSERT INTO atoms (id, type, content, hash, last_witnessed, domain)
                VALUES (?, 'file', ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    hash = excluded.hash,
                    last_witnessed = excluded.last_witnessed,
                    domain = excluded.domain
            """
            
            # Check for existing atom to fossilize
            cursor.execute("SELECT content, hash, last_witnessed, status FROM atoms WHERE id = ?", (rel_path,))
            existing = cursor.fetchone()
            
            if existing:
                old_content, old_hash, old_last_witnessed, old_status = existing
                
                # Only fossilize if content has changed
                if old_hash != file_hash:
                    fossil_timestamp = datetime.datetime.now().isoformat()
                    fossil_id = f"{rel_path}@{fossil_timestamp}"
                    
                    cursor.execute("""
                        INSERT INTO atoms (id, type, content, hash, last_witnessed, status, domain)
                        VALUES (?, 'file', ?, ?, ?, 4, 'Fossil')
                    """, (fossil_id, old_content, old_hash, old_last_witnessed))
                    
                    # Copy Geometry
                    cursor.execute("SELECT x, y FROM geometry WHERE atom_id = ?", (rel_path,))
                    geo = cursor.fetchone()
                    if geo:
                        cursor.execute("INSERT INTO geometry (atom_id, x, y) VALUES (?, ?, ?)", (fossil_id, geo[0], geo[1]))
                        
            cursor.execute(query, (rel_path, content, file_hash, timestamp, domain))
            print(f"Shattered: {rel_path} (Domain: {domain})")
            
    conn.commit()

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found. Run 'make setup' first.")
        exit(1)
        
    conn = init_db()
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', help='Relative path/ID of the atom')
    parser.add_argument('--content', help='Direct content for the atom')
    args = parser.parse_args()

    if args.path:
        project_root = os.getcwd()
        # Direct content mode (Hollow Construct)
        if args.content is not None:
            content = args.content
            file_hash = calculate_hash(content)
            timestamp = datetime.datetime.now().isoformat()
            domain = 'generic' # Hollow constructs are generic
            
            cursor = conn.cursor()
            query = """
                INSERT INTO atoms (id, type, content, hash, last_witnessed, domain)
                VALUES (?, 'file', ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    hash = excluded.hash,
                    last_witnessed = excluded.last_witnessed,
                    domain = excluded.domain
            """
            cursor.execute(query, (args.path, content, file_hash, timestamp, domain))
            conn.commit()
            print(f"ATOM_ID: {args.path}")
            
        # Single file mode
        else:
            full_path = os.path.abspath(args.path)
            if not os.path.exists(full_path):
                print(f"Error: File {full_path} not found")
                exit(1)
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            rel_path = os.path.relpath(full_path, project_root)
            file_hash = calculate_hash(content)
            timestamp = datetime.datetime.now().isoformat()
            domain = detect_domain(os.path.basename(full_path), content)
            
            cursor = conn.cursor()
            query = """
                INSERT INTO atoms (id, type, content, hash, last_witnessed, domain)
                VALUES (?, 'file', ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    hash = excluded.hash,
                    last_witnessed = excluded.last_witnessed,
                    domain = excluded.domain
            """
            
            # Check for existing atom to fossilize
            cursor.execute("SELECT content, hash, last_witnessed, status FROM atoms WHERE id = ?", (rel_path,))
            existing = cursor.fetchone()
            
            if existing:
                old_content, old_hash, old_last_witnessed, old_status = existing
                
                # Only fossilize if content has changed
                if old_hash != file_hash:
                    # Create Fossil ID
                    # We use the current timestamp for the ID uniqueness, representing when it became a fossil
                    fossil_timestamp = datetime.datetime.now().isoformat()
                    fossil_id = f"{rel_path}@{fossil_timestamp}"
                    
                    print(f"Fossilizing {rel_path} -> {fossil_id}")
                    
                    # 1. Insert Fossil Record (Status 4)
                    # We preserve the old content and hash. 
                    cursor.execute("""
                        INSERT INTO atoms (id, type, content, hash, last_witnessed, status, domain)
                        VALUES (?, 'file', ?, ?, ?, 4, 'Fossil')
                    """, (fossil_id, old_content, old_hash, old_last_witnessed))
                    
                    # 2. Copy Geometry
                    cursor.execute("SELECT x, y FROM geometry WHERE atom_id = ?", (rel_path,))
                    geo = cursor.fetchone()
                    if geo:
                        cursor.execute("INSERT INTO geometry (atom_id, x, y) VALUES (?, ?, ?)", (fossil_id, geo[0], geo[1]))

            cursor.execute(query, (rel_path, content, file_hash, timestamp, domain))
            conn.commit()
            print(f"ATOM_ID: {rel_path}")

    # Full scan mode
    else:
        shatter(conn)
    
    conn.close()
