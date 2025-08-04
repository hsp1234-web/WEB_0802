# debug/test_server_startup.py
import subprocess
import sys
import shutil
from pathlib import Path
import time
import os

# --- Configuration (from V56) ---
REPO_URL = "https://github.com/hsp1234-web/WEB_0802.git"
TARGET_BRANCH_OR_TAG = "0.7.0"
PROJECT_FOLDER_NAME = "debug_startup_test"
API_PORT = 8088

def log_header(title):
    print("\\n" + "="*80)
    print(f"=== {title.upper()} ===")
    print("="*80)

def run_and_print(command, cwd=None):
    """Runs a command and prints its output immediately."""
    print(f"\\n>> RUNNING: {' '.join(str(c) for c in command)}")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        cwd=cwd
    )
    print(f"   RETURN CODE: {result.returncode}")
    if result.stdout:
        print(f"   STDOUT:\\n---\\n{result.stdout.strip()}\\n---")
    if result.stderr:
        print(f"   STDERR:\\n---\\n{result.stderr.strip()}\\n---")
    return result.returncode == 0

def main():
    log_header("End-to-End Server Startup Test")
    base_path = Path(".") # Use current directory, not /content
    project_path = base_path / PROJECT_FOLDER_NAME

    try:
        # 1. Clean up
        log_header("Step 1: Cleaning up previous test environment")
        if project_path.exists():
            shutil.rmtree(project_path)
        print("Cleanup complete.")

        # 2. Clone repo
        log_header("Step 2: Cloning repository")
        if not run_and_print(["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPO_URL, str(project_path)]):
            sys.exit(1)

        # 3. Create venv
        log_header("Step 3: Creating virtual environment")
        venv_path = project_path / ".venv"
        if not run_and_print(["uv", "venv", str(venv_path)]):
            sys.exit(1)

        venv_python = venv_path / "bin" / "python"

        # 4. Bootstrap pip
        log_header("Step 4: Bootstrapping pip and wheel")
        if not run_and_print(["uv", "pip", "install", "--python", str(venv_python), "pip", "wheel"]):
            sys.exit(1)

        # 5. Install dependencies with the fix
        log_header("Step 5: Installing dependencies with --ignore-installed")
        core_requirements_path = project_path / "requirements/requirements-core.txt"
        pip_command = [
            str(venv_python), "-m", "pip", "install",
            "--ignore-installed",
            "-r", str(core_requirements_path)
        ]
        if not run_and_print(pip_command):
            sys.exit(1)

        print("\\n✅✅✅ Environment setup successful ✅✅✅")

        # 6. Launch Uvicorn and monitor
        log_header("Step 6: Launching Uvicorn Server")
        process_env = os.environ.copy()
        process_env.update({"VIRTUAL_ENV": str(venv_path), "PATH": f"{venv_path / 'bin'}:{os.environ.get('PATH', '')}", "PYTHONUNBUFFERED": "1"})
        uvicorn_command = [str(venv_python), "-m", "uvicorn", "src.phoenix_core.main:app", "--host", "0.0.0.0", "--port", str(API_PORT)]

        print(f"\\n>> LAUNCHING: {' '.join(uvicorn_command)}")
        server_process = subprocess.Popen(
            uvicorn_command,
            cwd=str(project_path),
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )

        start_time = time.monotonic()
        server_ready = False
        while time.monotonic() - start_time < 15: # Monitor for 15 seconds
            line = server_process.stdout.readline()
            if not line:
                break
            print(f"[SERVER LOG] {line.strip()}")
            if "Uvicorn running on" in line:
                server_ready = True
                break
            if "ERROR:" in line.upper() or "TRACEBACK" in line.upper():
                print("\\n❌❌❌ Server startup failed with an error! ❌❌❌")
                server_process.kill()
                sys.exit(1)

        if server_ready:
            print("\\n🎉🎉🎉 TEST PASSED! Server started successfully. 🎉🎉🎉")
            server_process.kill()
            sys.exit(0)
        else:
            print("\\n❌❌❌ TEST FAILED! Server did not start within 15 seconds. ❌❌❌")
            server_process.kill()
            sys.exit(1)

    except Exception as e:
        print(f"\\n🚨🚨🚨 An unexpected Python exception occurred during test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
