import pytest
import subprocess
import time
import requests
import wave
import sqlite3
from pathlib import Path

# --- Test Configuration ---
DB_PATH = Path("state.db")
UPLOAD_URL = "http://localhost:8080/transcribe/"
DUMMY_AUDIO_PATH = Path("tests/e2e/dummy_audio.wav")

def create_dummy_wav_file(duration_ms=100):
    """Creates a short, silent, mono WAV file."""
    n_channels = 1
    sampwidth = 2  # 16-bit
    framerate = 16000
    n_frames = int(framerate * (duration_ms / 1000.0))

    DUMMY_AUDIO_PATH.parent.mkdir(exist_ok=True)

    with wave.open(str(DUMMY_AUDIO_PATH), 'wb') as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.writeframes(b'\x00' * n_frames * n_channels * sampwidth)

@pytest.fixture(scope="module", autouse=True)
def live_server():
    """
    Fixture to start and stop the main application server for the test module.
    'autouse=True' ensures it runs for all tests in this module.
    """
    # Clean up old environment and DB
    subprocess.run("rm -rf .venv && rm -f state.db", shell=True, check=True)

    # Create a dummy audio file for testing
    create_dummy_wav_file()

    # Start the server
    server_process = subprocess.Popen(
        ["python", "local_run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for the server to be ready
    # We can poll the API or wait for a specific log message
    time.sleep(30) # Give it ample time to install deps and start

    yield

    # Teardown: stop the server
    server_process.terminate()
    try:
        server_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server_process.kill()

    # Clean up the dummy file
    if DUMMY_AUDIO_PATH.exists():
        DUMMY_AUDIO_PATH.unlink()

def poll_for_task_completion(task_id: str, timeout_seconds: int = 60) -> dict:
    """Polls the database until the task is completed or failed."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, result_text FROM transcription_tasks WHERE id = ?", (task_id,)
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0] in ["completed", "failed"]:
            return {"status": result[0], "result_text": result[1]}

        time.sleep(2)

    raise TimeoutError(f"Task {task_id} did not complete within {timeout_seconds} seconds.")

def test_transcription_flow():
    """
    Tests the full transcription flow:
    1. Upload a file.
    2. Get a task ID.
    3. Poll the DB for completion.
    4. Verify the result.
    """
    assert DUMMY_AUDIO_PATH.exists(), "Dummy audio file was not created"

    with open(DUMMY_AUDIO_PATH, 'rb') as f:
        files = {'file': (DUMMY_AUDIO_PATH.name, f, 'audio/wav')}
        response = requests.post(UPLOAD_URL, files=files)

    assert response.status_code == 200, f"API returned status {response.status_code}"
    response_data = response.json()
    assert "task_id" in response_data
    task_id = response_data["task_id"]

    final_status = poll_for_task_completion(task_id)

    assert final_status["status"] == "completed", f"Task failed, status was {final_status['status']}"
    # Since the audio is silent, the result should be an empty string
    assert final_status["result_text"] == "", f"Expected empty transcription but got: {final_status['result_text']}"
