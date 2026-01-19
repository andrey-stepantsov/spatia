
import pytest
import asyncio
from backend.connection_manager import ConnectionManager

@pytest.mark.asyncio
async def test_connection_manager_connect_disconnect():
    manager = ConnectionManager()
    
    # Test Connect
    queue = await manager.connect()
    assert queue in manager.clients
    assert len(manager.clients) == 1
    
    # Test Disconnect
    await manager.disconnect(queue)
    assert queue not in manager.clients
    assert len(manager.clients) == 0

@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    manager = ConnectionManager()
    
    queue1 = await manager.connect()
    queue2 = await manager.connect()
    
    data = {"type": "test", "content": "hello"}
    
    await manager.broadcast(data)
    
    # Check if both queues received the message
    msg1 = await queue1.get()
    msg2 = await queue2.get()
    
    expected_payload = 'data: {"type": "test", "content": "hello"}\n\n'
    
    assert msg1 == expected_payload
    assert msg2 == expected_payload

@pytest.mark.asyncio
async def test_connection_manager_disconnect_idempotency():
    manager = ConnectionManager()
    queue = await manager.connect()
    
    await manager.disconnect(queue)
    assert len(manager.clients) == 0
    
    # Should not raise error
    await manager.disconnect(queue)
    assert len(manager.clients) == 0
