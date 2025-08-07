import asyncio
import pytest
from datetime import datetime, timezone

# We need to add the src directory to the path for the import to work
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import the task
from phoenix_core.background.tasks import periodic_heartbeat

@pytest.mark.asyncio
async def test_simplified_heartbeat_runs(capsys):
    """
    Tests if the simplified heartbeat coroutine runs and prints output
    independently of the FastAPI application.
    """
    # Create the heartbeat task
    heartbeat_task = asyncio.create_task(periodic_heartbeat(interval_seconds=1))

    try:
        # Wait long enough for at least a few pings
        await asyncio.sleep(3.5)

    finally:
        # Ensure the task is cancelled to prevent it from running forever
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass  # This is the expected outcome of cancellation

    # Check the captured output
    captured = capsys.readouterr()
    print(f"Captured stdout: {captured.out}")
    print(f"Captured stderr: {captured.err}")

    assert "--- HEARTBEAT TASK STARTED ---" in captured.out
    assert "--- HEARTBEAT PING" in captured.out
    # Check for at least two pings
    assert captured.out.count("--- HEARTBEAT PING") >= 2
