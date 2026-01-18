#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
import sqlite3

def eject_workspace(name, workspaces_dir="workspaces"):
    target_dir = os.path.join(workspaces_dir, name)
    print(f"Ejecting workspace '{name}' from {target_dir}...")
    
    if not os.path.exists(target_dir):
        print(f"Error: Workspace {target_dir} not found.")
        sys.exit(1)

    # 1. Resolve Symlinks
    print(" resolving symlinks...")
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.islink(file_path):
                try:
                    target_path = os.readlink(file_path)
                    # Resolve relative to the link location if needed
                    if not os.path.isabs(target_path):
                        target_path = os.path.join(root, target_path)
                    
                    target_path = os.path.abspath(target_path)
                    
                    if os.path.exists(target_path) and os.path.isfile(target_path):
                        print(f"  Replacing symlink {file_path} with copy of {target_path}")
                        os.unlink(file_path)
                        shutil.copy2(target_path, file_path)
                    else:
                        print(f"  Warning: Symlink {file_path} points to missing locations {target_path}, skipping.")
                except Exception as e:
                    print(f"  Error resolving symlink {file_path}: {e}")

    # 2. Remove Metadata
    metadata_files = ["sentinel.db", "geometry.sp"]
    metadata_dirs = [".spatia"]
    
    for f in metadata_files:
        p = os.path.join(target_dir, f)
        if os.path.exists(p):
            print(f" Removing {p}")
            os.remove(p)
            
    for d in metadata_dirs:
        p = os.path.join(target_dir, d)
        if os.path.exists(p):
            print(f" Removing {p}")
            shutil.rmtree(p)
            
    print(f"Workspace '{name}' ejected successfully.")
    print(f"It is now a standalone directory at {target_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eject a Spatia workspace")
    parser.add_argument("name", help="Name of the workspace")
    args = parser.parse_args()
    
    eject_workspace(args.name)
