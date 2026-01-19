import asyncio
import json
from typing import List, Dict, Any

class ConnectionManager:
    def __init__(self):
        self.clients: List[asyncio.Queue] = []
        self.lock = asyncio.Lock()

    async def connect(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        async with self.lock:
            self.clients.append(queue)
        return queue

    async def disconnect(self, queue: asyncio.Queue):
        async with self.lock:
            if queue in self.clients:
                self.clients.remove(queue)

    async def broadcast(self, data: Dict[str, Any]):
        payload = f"data: {json.dumps(data)}\n\n"
        # Snapshot clients to avoid holding lock during iteration if we wanted, 
        # but asyncio lists are thread-safe(ish) in single event loop.
        # However, it's safer to copy the list or iterate directly if we are careful.
        # Let's use the lock to safe-guard the list access.
        
        async with self.lock:
            current_clients = list(self.clients)
            
        for queue in current_clients:
            await queue.put(payload)
