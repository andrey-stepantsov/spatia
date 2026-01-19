import asyncio # Touch to force reload
import json
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, Response, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import sqlite3
import subprocess
import datetime
import shutil
from pydantic import BaseModel

from watchfiles import awatch
from backend.projector import Projector

projector = Projector()

DB_PATH = '.spatia/sentinel.db'
SHATTER_SCRIPT = '.spatia/bin/spatia-shatter.py'

async def watch_sentinel_db():
    print(f"Starting Sentinel DB Watcher on {DB_PATH}...")
    try:
        # Debounce/Batched updates are handled by awatch yielding a set of changes
        async for changes in awatch(DB_PATH, step=500): # Check every 500ms
            print(f"Sentinel DB Changed: {changes}")
            # Broadcast a generic 'db_update' event to trigger refetch
            await broadcast_event({"type": "db_update"})
    except Exception as e:
        print(f"Watcher Error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Reset Zombie Atoms (Status 2 -> 1)
    # Startup
    try:
        # Connect (creates file if missing)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Reset Zombie Atoms (Status 2 -> 1) - Only if atoms table exists
        # We can try it, catch OperationalError if table missing
        try:
            cursor.execute("UPDATE atoms SET status = 1 WHERE status = 2")
            if cursor.rowcount > 0:
                print(f"Startup: Reset {cursor.rowcount} zombie witness(es) back to claim status.")
                conn.commit()
        except sqlite3.OperationalError:
            # Table probably doesn't exist yet, which is fine
            pass
        
        # 2. Ensure Schema
        
        # Ensure atoms table exists (missing from original lifespan, maybe it was manual?)
        # Adding it for completeness/tests
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

        # Ensure threads table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                source TEXT,
                target TEXT
            )
        """)
        
        # Ensure portals table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atom_id TEXT,
                path TEXT,
                description TEXT,
                created_at TEXT
            )
        """)

        # Ensure envelopes table exists (Phase II)
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
        
        # Ensure geometry table (used in main.py but not in original setup?)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS geometry (
                atom_id TEXT PRIMARY KEY,
                x INTEGER,
                y INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Startup Error: Failed to init DB: {e}")
    
    # Start Background Watcher
    global watcher_task
    watcher_task = asyncio.create_task(watch_sentinel_db())
    
    yield
    
    # Shutdown
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        print("Sentinel Watcher Stopped")

    try:
        await watcher_task
    except asyncio.CancelledError:
        print("Sentinel Watcher Stopped")

# Refactored Connection Manager
from backend.connection_manager import ConnectionManager
manager = ConnectionManager()

async def broadcast_event(data: dict):
    await manager.broadcast(data)

app = FastAPI(lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback



# Concurrency Helpers
from functools import partial
async def run_in_thread(func, *args, **kwargs):
    return await asyncio.get_running_loop().run_in_executor(None, partial(func, *args, **kwargs))

# Global Locks
workspace_lock = asyncio.Lock()
watcher_task: Optional[asyncio.Task] = None

@app.get("/api/workspaces")
async def get_workspaces():
    workspaces = []
    if os.path.exists("workspaces"):
        for name in os.listdir("workspaces"):
            ws_path = os.path.join("workspaces", name)
            if os.path.isdir(ws_path):
                # Only include if it has sentinel.db (i.e. it is a Spatia workspace)
                if os.path.exists(os.path.join(ws_path, "sentinel.db")):
                    workspaces.append(name)
    return sorted(workspaces)

class WorkspaceSwitch(BaseModel):
    name: str

@app.post("/api/workspace/switch")
async def switch_workspace(req: WorkspaceSwitch):
    # Protect workspace switching with a lock to prevent race conditions
    async with workspace_lock:
        global watcher_task
        target_ws = req.name
        ws_path = os.path.join("workspaces", target_ws)
        
        if not os.path.exists(ws_path):
            raise HTTPException(status_code=404, detail="Workspace not found")
            
        print(f"Switching to workspace: {target_ws}")

        # 1. Stop Watcher
        if watcher_task and not watcher_task.done():
            print("Stopping DB Watcher...")
            watcher_task.cancel()
            try:
                await watcher_task
            except asyncio.CancelledError:
                pass
                
        # 2. Update Symlinks
        # Remove old symlinks
        try:
            if os.path.islink(DB_PATH) or os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            geo_link = ".spatia/geometry.sp"
            if os.path.islink(geo_link) or os.path.exists(geo_link):
                os.remove(geo_link)
        except Exception as e:
            print(f"Error removing links: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to remove symlinks: {e}")
            
        # Create new symlinks
        try:
            # Calculate relative paths to target workspace files
            # Target: workspaces/<name>/sentinel.db
            # Source: DB_PATH (e.g. .spatia/sentinel.db or test_sentinel.db)
            
            # 1. Sentinel DB
            target_db_abs = os.path.abspath(os.path.join("workspaces", target_ws, "sentinel.db"))
            link_db_dir = os.path.dirname(os.path.abspath(DB_PATH))
            rel_target_db = os.path.relpath(target_db_abs, link_db_dir)
            
            os.symlink(rel_target_db, DB_PATH)

            # 2. Geometry
            geo_link = ".spatia/geometry.sp"
            target_geo_abs = os.path.abspath(os.path.join("workspaces", target_ws, "geometry.sp"))
            link_geo_dir = os.path.dirname(os.path.abspath(geo_link))
            rel_target_geo = os.path.relpath(target_geo_abs, link_geo_dir)
            
            os.symlink(rel_target_geo, geo_link)
            
        except Exception as e:
            print(f"Error creating links: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create symlinks: {e}")
            
        print(f"Symlinks updated to {target_ws}")

        # 3. Restart Watcher
        watcher_task = asyncio.create_task(watch_sentinel_db())
        
        # 4. Broadcast Reset
        await broadcast_event({"type": "world_reset"})
        
        return {"status": "switched", "workspace": target_ws}




@app.post("/api/workspaces")
async def create_workspace(req: WorkspaceSwitch):
    # Reuse WorkspaceSwitch model as it has 'name' field
    name = req.name
    if not name or "/" in name or "\\" in name or name == ".." or name == ".":
         raise HTTPException(status_code=400, detail="Invalid workspace name")
         
    cmd = [".spatia/bin/spatia-init-workspace.py", name]
    output = await run_subprocess_async(cmd)
    
    return {"status": "created", "workspace": name, "output": output}

@app.post("/api/workspaces/{name}/snapshot")
async def snapshot_workspace(name: str):
    ws_path = os.path.join("workspaces", name)
    if not os.path.isdir(ws_path):
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    db_path = os.path.join(ws_path, "sentinel.db")
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Sentinel DB not found in workspace")
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    snap_path = os.path.join(ws_path, f"sentinel.snap.{timestamp}.db")
    
    try:
        await run_in_thread(shutil.copy2, db_path, snap_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to snapshot: {e}")
        
    return {"status": "snapshotted", "workspace": name, "snapshot": f"sentinel.snap.{timestamp}.db"}

class CloneRequest(BaseModel):
    new_name: Optional[str] = None

@app.post("/api/workspaces/{name}/clone")
async def clone_workspace(name: str, req: CloneRequest = Body(default=None)):
    src_path = os.path.join("workspaces", name)
    if not os.path.isdir(src_path):
         raise HTTPException(status_code=404, detail="Workspace not found")
         
    if req and req.new_name:
        target_name = req.new_name
    else:
        target_name = f"{name}-copy"

    target_path = os.path.join("workspaces", target_name)
    
    # Handle collision if auto-generated, or error if explicit?
    # If explicit name provided, we should probably fail if it exists or handle it?
    # Let's keep collision handling for auto, but for explicit, let's fail if exists to be safe/clear.
    if req and req.new_name and os.path.exists(target_path):
         raise HTTPException(status_code=409, detail="Target workspace already exists")
    
    # Auto-generation collision handling
    counter = 1
    while os.path.exists(target_path):
        target_name = f"{name}-copy-{counter}"
        target_path = os.path.join("workspaces", target_name)
        counter += 1
        
    try:
        await run_in_thread(shutil.copytree, src_path, target_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone: {e}")
        
    return {"status": "cloned", "source": name, "target": target_name}

@app.post("/api/workspaces/{name}/eject")
async def eject_workspace(name: str):
    # Invoke spatia-eject.py
    # We pass the workspace NAME, the script should resolve it.
    
    cmd = [".spatia/bin/spatia-eject.py", name]
    output = await run_subprocess_async(cmd)
    
    await broadcast_event({"type": "world_ejected", "workspace": name})
    return {"status": "ejected", "workspace": name, "output": output}

SHATTER_SCRIPT = '.spatia/bin/spatia-shatter.py'

class ShatterRequest(BaseModel):
    path: str
    content: Optional[str] = None

class GeometryUpdate(BaseModel):
    atom_id: str
    x: int
    y: int

class Thread(BaseModel):
    source: str
    target: str

class PortalCreate(BaseModel):
    atom_id: str
    path: str
    description: Optional[str] = None

class Portal(BaseModel):
    id: int
    atom_id: str
    path: str
    description: Optional[str]
    created_at: str

class SummonRequest(BaseModel):
    atom_id: str
    model: Optional[str] = "gemini-2.5-flash"

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
             err_msg = stderr.decode()
             print(f"Subprocess Failed: {cmd}")
             print(f"Stdout: {stdout.decode()}")
             print(f"Stderr: {err_msg}")
             # Include stdout in detail as scripts might print errors there
             detail_msg = f"Script execution failed. Stderr: {err_msg}. Stdout: {stdout.decode()}"
             raise HTTPException(status_code=500, detail=detail_msg)
             
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
    print(f"Received Shatter Request: {request}")
    try:
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"SHATTER EXCEPTION: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/api/threads")
async def get_threads():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source, target FROM threads")
        return [dict(row) for row in cursor.fetchall()]

@app.post("/api/threads")
async def create_thread(thread: Thread):
    import uuid
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Check if exists first to avoid duplicate logic with different ID
        # (Though PK is ID, we might want unique source-target pair?)
        # Original code used IGNORE on composite PK.
        # Let's try to query first.
        cursor.execute("SELECT id FROM threads WHERE source = ? AND target = ?", (thread.source, thread.target))
        existing = cursor.fetchone()
        
        if not existing:
             new_id = str(uuid.uuid4())
             cursor.execute("INSERT INTO threads (id, source, target) VALUES (?, ?, ?)", (new_id, thread.source, thread.target))
             conn.commit()
    
    await broadcast_event({"type": "thread_new", "source": thread.source, "target": thread.target})
    return {"status": "ok"}

@app.get("/api/portals/{atom_id}")
async def get_portals(atom_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portals WHERE atom_id = ?", (atom_id,))
        return [dict(row) for row in cursor.fetchall()]

@app.post("/api/portals")
async def create_portal(portal: PortalCreate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        import datetime
        created_at = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO portals (atom_id, path, description, created_at) VALUES (?, ?, ?, ?)",
            (portal.atom_id, portal.path, portal.description, created_at)
        )
        conn.commit()
    return {"status": "ok"}

@app.post("/api/summon")
async def summon_atom(request: SummonRequest, background_tasks: BackgroundTasks):
    atom_id = request.atom_id
    
    # 1. OPTIMISTIC LOCKING: Reserve access (Status 0 -> 2)
    # Status 2 (Witnessing) also serves as "Processing/Busy" here
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check current status first for better error message
        cursor.execute("SELECT status FROM atoms WHERE id = ?", (atom_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Atom not found")
        
        if row['status'] != 0:
            raise HTTPException(status_code=400, detail=f"Atom is not in Hollow state (Status 0). Current: {row['status']}")

        # Attempt atomic reservation
        cursor.execute("UPDATE atoms SET status = 2 WHERE id = ? AND status = 0", (atom_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            # Race condition hit - someone else just took it or it changed status
            raise HTTPException(status_code=409, detail="Atom was modified by another process (Optimistic lock failed)")

    # Notify we are starting (processing)
    await broadcast_event({"type": "update", "atom_id": atom_id})
    
    try:
        # 2. Fetch Context Data
        with get_db_connection() as conn:
             cursor = conn.cursor()
             
             # Fetch content again? Yes, it should be safe now we have lock.
             cursor.execute("SELECT content, domain FROM atoms WHERE id = ?", (atom_id,))
             row = cursor.fetchone()
             content = row['content']
             domain = row['domain']
             
             cursor.execute("SELECT * FROM portals WHERE atom_id = ?", (atom_id,))
             portals = [dict(r) for r in cursor.fetchall()]
             
             cursor.execute("SELECT target FROM threads WHERE source = ?", (atom_id,))
             neighbors = [r['target'] for r in cursor.fetchall()]

        # 3. Generate Content (Offloaded to avoid blocking main loop)
        new_content = await run_in_thread(
            projector.summon, 
            atom_id, content, portals, neighbors, request.model, domain
        )
        
        # Strip Markdown Code Blocks
        if new_content.strip().startswith("```"):
             lines = new_content.strip().split("\n")
             if lines[0].startswith("```"): lines = lines[1:]
             if lines and lines[-1].startswith("```"): lines = lines[:-1]
             new_content = "\n".join(lines)
        
        # 4. Update DB (Status 2 -> 1 Claim)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE atoms SET content = ?, status = 1 WHERE id = ?", (new_content, atom_id))
            conn.commit()

        # Broadcast Claim
        await broadcast_event({"type": "update", "atom_id": atom_id})

        # 5. Write to Disk (Offloaded)
        if os.path.exists(atom_id):
             def write_file():
                 with open(atom_id, "w") as f:
                     f.write(new_content)
             await run_in_thread(write_file)

        # 6. Trigger Witness (Status 1 -> 2 -> 3)
        # Note: We just set it to 1. Now we trigger witness which sets it to 2 again.
        with get_db_connection() as conn:
             conn.execute("UPDATE atoms SET status = 2 WHERE id = ?", (atom_id,))
             conn.commit()
             
        background_tasks.add_task(run_witness_process, atom_id)
        
        await broadcast_event({"type": "update", "atom_id": atom_id})
        return {"status": "summoned", "atom_id": atom_id, "model": request.model}
        
    except Exception as e:
        print(f"Summon Error: {e}")
        # Failure Recovery: Revert Status to 0 or 1?
        # If we failed during generation, it acts like it never happened?
        # Revert to 1 (Claim) with old content? OR 0 (Hollow)?
        # If we revert to 0, user can try again easily.
        with get_db_connection() as conn:
             try:
                 # Check what status is now? We held it at 2 (since we set it).
                 conn.execute("UPDATE atoms SET status = 0 WHERE id = ?", (atom_id,))
                 conn.commit()
             except:
                 pass
        
        await broadcast_event({"type": "update", "atom_id": atom_id})
        raise HTTPException(status_code=500, detail=f"Summon failed: {e}")

class WitnessRequest(BaseModel):
    atom_id: str

async def run_witness_process(atom_id: str):
    """
    Executes the Witness Router script.
    Exit Code 0 -> Status 3 (Endorsed)
    Exit Code * -> Status 1 (Claim)
    """
    print(f"Background: Witnessing {atom_id}...")
    WITNESS_SCRIPT = os.environ.get("WITNESS_SCRIPT", '.spatia/bin/spatia-witness-router')
    
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

    # Notify immediate change
    await broadcast_event({"type": "update", "atom_id": request.atom_id})

    return {"status": "witnessing", "atom_id": request.atom_id}

class ReviveRequest(BaseModel):
    fossil_id: str

@app.post("/api/revive")
async def revive_atom(request: ReviveRequest):
    fossil_id = request.fossil_id
    
    if '@' not in fossil_id:
        raise HTTPException(status_code=400, detail="Invalid fossil ID format")
        
    original_id = fossil_id.split('@')[0]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch Fossil Content
        cursor.execute("SELECT content, hash, last_witnessed FROM atoms WHERE id = ?", (fossil_id,))
        fossil = cursor.fetchone()
        if not fossil:
             raise HTTPException(status_code=404, detail="Fossil not found")
        fossil_content, fossil_hash, fossil_last_witnessed = fossil
        
        # 2. Fetch Current Content (to fossilize it)
        cursor.execute("SELECT content, hash, last_witnessed FROM atoms WHERE id = ?", (original_id,))
        current = cursor.fetchone()
        
        if current:
            curr_content, curr_hash, curr_last_witnessed = current
            
            # Fossilize current state
            new_fossil_ts = datetime.datetime.now().isoformat()
            new_fossil_id = f"{original_id}@{new_fossil_ts}"
            
            cursor.execute("""
                INSERT INTO atoms (id, type, content, hash, last_witnessed, status)
                VALUES (?, 'file', ?, ?, ?, 4)
            """, (new_fossil_id, curr_content, curr_hash, curr_last_witnessed))
            
            # Copy Geometry
            cursor.execute("SELECT x, y FROM geometry WHERE atom_id = ?", (original_id,))
            geo = cursor.fetchone()
            if geo:
                 cursor.execute("INSERT INTO geometry (atom_id, x, y) VALUES (?, ?, ?)", (new_fossil_id, geo[0], geo[1]))
                 
        # 3. Promote Fossil to Current (Status 1 - Claim, needing verification if it was endorsed? Yes, revive -> Claim)
        # We update the content to match the fossil.
        # Note: We should probably update the hash too.
        cursor.execute("""
            UPDATE atoms 
            SET content = ?, hash = ?, status = 1 
            WHERE id = ?
        """, (fossil_content, fossil_hash, original_id))
        
        conn.commit()
    
    # 4. Trigger Materialization (write to disk)
    MATERIALIZE_SCRIPT = '.spatia/bin/spatia-materialize.py'
    await run_subprocess_async([MATERIALIZE_SCRIPT])
    
    await broadcast_event({"type": "update", "atom_id": original_id})
    # Also notify about the new fossil (current became fossil) and the revived fossil?
    # Actually, we refreshed the list.
    
    return {"status": "revived", "atom_id": original_id}

@app.get("/api/events")
async def sse_endpoint():
    queue = await manager.connect()
    async def event_generator():
        try:
            yield "event: connected\ndata: {}\n\n"
            await asyncio.sleep(0.01) # Yield control to allow flush
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            await manager.disconnect(queue)
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


class EnvelopeCreate(BaseModel):
    id: str
    domain: Optional[str] = "generic"
    x: int
    y: int
    w: int
    h: int

class EnvelopeUpdate(BaseModel):
    domain: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    w: Optional[int] = None
    h: Optional[int] = None



@app.post("/api/echo")
async def echo_request(request: Request):
    """
    Echo endpoint for network RTT measurement.
    Broadcasts 'echo_response' to all clients.
    """
    import time
    body = await request.json()
    client_ts = body.get("timestamp")
    payload = body.get("payload", "")
    
    server_ts = time.time() * 1000 # ms
    
    await broadcast_event({
        "type": "echo_response",
        "client_timestamp": client_ts,
        "server_timestamp": server_ts,
        "payload": payload
    })
    
    return {"status": "ok", "server_timestamp": server_ts}

@app.get("/api/envelopes")
async def get_envelopes():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM envelopes")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return []

@app.post("/api/envelopes")
async def create_envelope(env: EnvelopeCreate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO envelopes (id, domain, x, y, w, h)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (env.id, env.domain, env.x, env.y, env.w, env.h))
            conn.commit()
        except sqlite3.IntegrityError:
             raise HTTPException(status_code=409, detail="Envelope ID already exists")
    
    await broadcast_event({"type": "envelope_update", "id": env.id})
    return {"status": "created", "envelope": env.model_dump()}

@app.put("/api/envelopes/{env_id}")
async def update_envelope(env_id: str, updates: EnvelopeUpdate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Build dynamic query
        fields = []
        values = []
        if updates.domain is not None:
            fields.append("domain = ?")
            values.append(updates.domain)
        if updates.x is not None:
            fields.append("x = ?")
            values.append(updates.x)
        if updates.y is not None:
            fields.append("y = ?")
            values.append(updates.y)
        if updates.w is not None:
            fields.append("w = ?")
            values.append(updates.w)
        if updates.h is not None:
            fields.append("h = ?")
            values.append(updates.h)
            
        if not fields:
            return {"status": "no_change"}
            
        values.append(env_id)
        
        cursor.execute(f"UPDATE envelopes SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    
    await broadcast_event({"type": "envelope_update", "id": env_id})
    return {"status": "updated", "id": env_id}

# --- Connection Manager & Diagnostics ---

@app.get("/api/health")
async def health_check():
    """
    Heartbeat endpoint for frontend to verify backend availability.
    """
    # Check DB connection
    db_status = "unknown"
    workspace_name = "unknown"
    
    try:
        # Check if we can connect
        if os.path.exists(DB_PATH):
           with sqlite3.connect(DB_PATH) as conn:
               cursor = conn.cursor()
               cursor.execute("SELECT 1")
               db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        
    # Determine current workspace
    try:
        if os.path.islink(DB_PATH):
            real_path = os.readlink(DB_PATH)
            parts = real_path.split(os.sep)
            if "workspaces" in parts:
                idx = parts.index("workspaces")
                if len(parts) > idx + 1:
                    workspace_name = parts[idx + 1]
        else:
            workspace_name = "default"
    except Exception:
        workspace_name = "unknown"

    return {
        "status": "ok",
        "service": "spatia-backend",
        "db_status": db_status,
        "workspace": workspace_name,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global Exception: {exc}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "type": type(exc).__name__
            }
        },
        status_code=500
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        content={
            "status": "error",
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        },
        status_code=exc.status_code
    )



@app.delete("/api/envelopes/{envelope_id}")
async def delete_envelope(envelope_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM envelopes WHERE id = ?", (envelope_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Envelope not found")
        conn.commit()
    
    await broadcast_event({"type": "envelope_delete", "id": envelope_id})

    return {"status": "deleted", "id": envelope_id}


