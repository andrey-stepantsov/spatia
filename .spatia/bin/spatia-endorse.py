#!/usr/bin/env python3
import sqlite3
import sys

DB_PATH = '.spatia/sentinel.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def endorse(conn, target_id=None):
    cursor = conn.cursor()
    if target_id:
        cursor.execute("UPDATE atoms SET status = 1 WHERE id = ?", (target_id,))
        print(f"Endorsed atom: {target_id}")
    else:
        cursor.execute("UPDATE atoms SET status = 1 WHERE status = 0")
        print("Endorsed all pending atoms.")
    conn.commit()

if __name__ == '__main__':
    conn = init_db()
    if len(sys.argv) > 1:
        endorse(conn, sys.argv[1])
    else:
        endorse(conn)
    conn.close()
