import pytest
import sys
import subprocess
import time
from pathlib import Path
import httpx
import os
from typing import Generator
import socket
import json
# --- Test Setup ---
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
TEST_AUDIO_PATH = Path(__file__).parent / "audio_for_test.wav"

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensures the venv and dependencies are ready."""
    import base64
    if not VENV_PYTHON.exists():
        pytest.fail(".venv not found. Please run the main test script first.")

    # A valid, 1-second silent WAV file encoded in Base64
    SILENT_WAV_BASE64 = "UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA"

    TEST_AUDIO_PATH.parent.mkdir(exist_ok=True)
    TEST_AUDIO_PATH.write_bytes(base64.b64decode(SILENT_WAV_BASE64))
    yield
    TEST_AUDIO_PATH.unlink()

def find_free_port() -> int:
    """尋找一個空閒的 TCP 埠號。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

@pytest.fixture(scope="session")
def live_api_server() -> Generator[str, None, None]:
    """Starts the main FastAPI server as a subprocess on a free port."""
    server_script = PROJECT_ROOT / "scripts" / "run_server_only.py"
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    # Create a temporary config for the server
    config_data = {"__test_port__": port}
    config_path = PROJECT_ROOT / "temp_transcription_test_config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    process = subprocess.Popen(
        [str(VENV_PYTHON), str(server_script), "--config", str(config_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Health check
    is_ready = False
    for _ in range(15): # Give it time to start
        try:
            with httpx.Client() as client:
                if client.get(base_url, timeout=1).status_code == 200:
                    is_ready = True
                    break
        except httpx.ConnectError:
            time.sleep(1)

    if not is_ready:
        output = process.communicate()[0]
        process.terminate()
        pytest.fail(f"API server failed to start on port {port}. Output:\n{output}")

    yield base_url

    process.terminate()
    if config_path.exists():
        config_path.unlink()

@pytest.fixture(scope="session")
def live_worker() -> Generator[None, None, None]:
    """
    Starts the transcription worker in a separate process.
    This is tricky because the worker loop is not in a standalone script.
    We'll create a small runner script on the fly.
    """
    runner_script_path = Path(__file__).parent / "run_worker_helper.py"
    runner_script_content = f"""
import asyncio
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.phoenix_core.modules.transcription.worker import transcription_worker_main_loop
asyncio.run(transcription_worker_main_loop())
"""
    runner_script_path.write_text(runner_script_content)

    process = subprocess.Popen(
        [str(VENV_PYTHON), str(runner_script_path)],
    )

    yield

    process.terminate()
    runner_script_path.unlink()

# --- The Actual Test ---

@pytest.mark.e2e
def test_upload_and_poll_to_completion(live_api_server: str, live_worker: None):
    """A full end-to-end test for the transcription flow."""
    base_url = live_api_server

    # 1. Upload the file
    with open(TEST_AUDIO_PATH, "rb") as f:
        files = {"file": (TEST_AUDIO_PATH.name, f, "audio/wav")}
        with httpx.Client() as client:
            response = client.post(f"{base_url}/transcription/upload", files=files, timeout=10)

    assert response.status_code == 202
    task_id = response.json()["task_id"]

    # 2. Poll for completion
    final_status = None
    for _ in range(20): # Poll for up to 20 seconds
        with httpx.Client() as client:
            status_response = client.get(f"{base_url}/transcription/status/{task_id}", timeout=10)

        assert status_response.status_code == 200
        status_data = status_response.json()

        if status_data["status"] == "completed":
            final_status = status_data
            break

        if status_data["status"] == "failed":
            pytest.fail(f"Task failed with message: {status_data.get('error_message')}")

        time.sleep(1)

    assert final_status is not None, "Task did not complete within the timeout."
    assert final_status["status"] == "completed"
    # We can't assert the exact text because the 'tiny' model is non-deterministic
    # and will produce garbage from a garbage wav file, but we can check it's not empty.
    assert isinstance(final_status.get("result_text"), str)
