import asyncio
import json
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
import os
import sqlite3
import subprocess
from pydantic import BaseModel

DB_PATH = '.spatia/sentinel.db'

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Reset Zombie Atoms (Status 2 -> 1)
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE atoms SET status = 1 WHERE status = 2")
            if cursor.rowcount > 0:
                print(f"Startup: Reset {cursor.rowcount} zombie witness(es) back to claim status.")
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Startup Error: Failed to reset zombie atoms: {e}")
    
    yield
    # Shutdown logic (if any) here


clients: List[asyncio.Queue] = []

async def broadcast_event(data: dict):
    payload = f"data: {json.dumps(data)}\n\n"
    # Iterate over a copy to safely handle modifications if any (though asyncio is single threaded)
    for queue in clients:
        await queue.put(payload)

app = FastAPI(lifespan=lifespan)



SHATTER_SCRIPT = '.spatia/bin/spatia-shatter.py'

class ShatterRequest(BaseModel):
    path: str
    content: Optional[str] = None

class GeometryUpdate(BaseModel):
    atom_id: str
    x: int
    y: int

async def run_subprocess_async(cmd, env=None):
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
             raise HTTPException(status_code=500, detail=f"Script execution failed: {stderr.decode()}")
             
        return stdout.decode().strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Sentinel DB not found")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.post("/api/shatter")
async def shatter_atom(request: ShatterRequest):
    cmd = [SHATTER_SCRIPT, '--path', request.path]
    if request.content is not None:
        cmd.extend(['--content', request.content])
    
    output = await run_subprocess_async(cmd)
    
    # Parse output for ATOM_ID: <id>
    atom_id = None
    for line in output.split('\n'):
        if line.startswith('ATOM_ID:'):
            atom_id = line.split(':', 1)[1].strip()
            break
            
    if not atom_id:
        # Fallback if script didn't output ID cleanly (shouldn't happen with our update)
        # Or if it was a re-shatter of existing file, maybe we just use request.path
        # But we want to be sure.
        raise HTTPException(status_code=500, detail=f"Could not determine atom_id from script output: {output}")

    # Ensure geometry exists
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO geometry (atom_id, x, y) VALUES (?, 0, 0)", (atom_id,))
        conn.commit()

    await broadcast_event({"type": "update", "atom_id": atom_id})
    return {"atom_id": atom_id}

@app.get("/api/atoms")
async def get_atoms():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Ensure we select status and domain as requested
        cursor.execute("""
            SELECT a.*, COALESCE(g.x, 0) as x, COALESCE(g.y, 0) as y 
            FROM atoms a 
            LEFT JOIN geometry g ON a.id = g.atom_id
        """)
        atoms = [dict(row) for row in cursor.fetchall()]
        
        # Also fetch geometry to merge? User just asked ensure status/domain.
        # But for frontend rendering, geometry matches are usually needed.
        # The prompt only said "GET /api/atoms endpoint that performs a direct SELECT * FROM atoms".
        # It didn't say join geometry.
        
    return atoms

@app.post("/api/geometry")
async def update_geometry(updates: List[GeometryUpdate]):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for update in updates:
            cursor.execute("""
                INSERT INTO geometry (atom_id, x, y) 
                VALUES (?, ?, ?)
                ON CONFLICT(atom_id) DO UPDATE SET
                    x = excluded.x,
                    y = excluded.y
            """, (update.atom_id, update.x, update.y))
        conn.commit()
    return {"status": "ok"}

class WitnessRequest(BaseModel):
    atom_id: str

async def run_witness_process(atom_id: str):
    """
    Executes the Witness Router script.
    Exit Code 0 -> Status 3 (Endorsed)
    Exit Code * -> Status 1 (Claim)
    """
    print(f"Background: Witnessing {atom_id}...")
    WITNESS_SCRIPT = '.spatia/bin/spatia-witness-router'
    
    # Notify start (optional, already done in endpoint, but good for consistency)
    await broadcast_event({"type": "update", "atom_id": atom_id})

    try:
        # Run the script with updated environment
        env = os.environ.copy()
        env['SENTINEL_DB'] = DB_PATH
        
        # Use async subprocess
        process = await asyncio.create_subprocess_exec(
            WITNESS_SCRIPT, atom_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        stdout, stderr = await process.communicate()
        exit_code = process.returncode
        
        print(f"Background: Witness finished with code {exit_code}")
        
        new_status = 3 if exit_code == 0 else 1
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE atoms SET status = ? WHERE id = ?", (new_status, atom_id))
            conn.commit()
            
    except Exception as e:
        print(f"Background: Witness failed to execute: {e}")
        # Revert to Claim on system failure
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE atoms SET status = 1 WHERE id = ?", (atom_id,))
            conn.commit()

    # Notify completion
    await broadcast_event({"type": "update", "atom_id": atom_id})

@app.post("/api/witness")
async def witness_atom(request: WitnessRequest, background_tasks: BackgroundTasks):
    # 1. Immediate Transition to Status 2 (Witnessing)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE atoms SET status = 2 WHERE id = ?", (request.atom_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Atom not found")
        conn.commit()
        
    # 2. Schedule Background Logic
    background_tasks.add_task(run_witness_process, request.atom_id)
    
    # Notify immediate change
    await broadcast_event({"type": "update", "atom_id": request.atom_id})

    return {"status": "witnessing", "atom_id": request.atom_id}

@app.get("/api/events")
async def sse_endpoint():
    queue = asyncio.Queue()
    clients.append(queue)
    async def event_generator():
        yield "event: connected\ndata: {}\n\n"
        await asyncio.sleep(0.01) # Yield control to allow flush
        try:
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            clients.remove(queue)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/atoms/{atom_id}/logs")
async def get_atom_logs(atom_id: str):
    log_path = f".spatia/logs/{atom_id}.log"
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Logs not found for this atom")
    
    try:
        with open(log_path, "r") as f:
            content = f.read()
        return {"atom_id": atom_id, "logs": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e}")
