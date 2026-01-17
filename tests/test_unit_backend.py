
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import backend.main
from backend.main import watch_sentinel_db, run_witness_process

@pytest.mark.anyio
async def test_watch_sentinel_db_flow():
    """Test that watch_sentinel_db broadcasts events on file changes."""
    
    async def mock_changes(*args, **kwargs):
        yield {('modified', 'sentinel.db')}

    with patch('backend.main.awatch', side_effect=mock_changes):
        with patch('backend.main.broadcast_event', new_callable=AsyncMock) as mock_broadcast:
            await watch_sentinel_db()
            mock_broadcast.assert_called_with({"type": "db_update"})

@pytest.mark.anyio
async def test_watch_sentinel_db_error_handling():
    """Test that watch_sentinel_db handles exceptions gracefully."""
    
    async def mock_error(*args, **kwargs):
        raise Exception("Watcher crashed")
        yield # Make it a generator

    with patch('backend.main.awatch', side_effect=mock_error):
        with patch('builtins.print') as mock_print:
            await watch_sentinel_db()
            mock_print.assert_any_call("Watcher Error: Watcher crashed")

@pytest.mark.anyio
async def test_run_witness_process_exception():
    """Test handling of subprocess execution failure."""
    
    atom_id = "test_atom_error"
    
    with patch('asyncio.create_subprocess_exec', side_effect=OSError("Nix missing")):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        
        with patch('backend.main.get_db_connection', return_value=mock_conn):
             with patch('os.environ.copy', return_value={}):
                 with patch('builtins.print') as mock_print:
                     await run_witness_process(atom_id)
                     
                     # Check error log
                     found_error = any("Witness failed to execute" in str(arg) for args, _ in mock_print.call_args_list for arg in args)
                     assert found_error, "Error message not printed"
                     
                     # Check DB update
                     mock_cursor.execute.assert_called()
                     sql, params = mock_cursor.execute.call_args[0]
                     
                     # Check SQL sets status = 1
                     assert "UPDATE atoms SET status = 1" in sql
                     # Check atom_id param
                     assert params[0] == atom_id

