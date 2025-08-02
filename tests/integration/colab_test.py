# 檔案: tests/integration/colab_test.py
import sys
import os
import subprocess
import time
import pytest
import httpx
import tempfile
import json
import socket
from pathlib import Path

# --- 測試設定 ---
SERVER_START_TIMEOUT = 120
POLL_INTERVAL = 2
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# --- 輔助函式 ---

def run_command(command, cwd, env=None):
    print(f"\n🚀 執行命令: {' '.join(command)}")
    result = subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8'
    )
    if result.returncode != 0:
        print(f"❌ 命令執行失敗!\n   STDOUT: {result.stdout}\n   STDERR: {result.stderr}")
    assert result.returncode == 0, f"命令執行失敗: {command}"
    print("✅ 命令成功。")

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

# --- Pytest Fixture ---

@pytest.fixture(scope="module")
def live_server():
    """
    一個直接測試後端啟動器 (start_api_service.py) 的 fixture。
    這是最穩定、最核心的測試。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # --- 準備環境 ---
        port = find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        config_data = {
            "system_settings": {"timezone": "UTC"},
            "__test_port__": port  # 將動態埠號寫入設定檔
        }
        config_path = tmp_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # --- 啟動後端服務 ---
        # 我們直接執行 start_api_service.py，因為它包含了完整的環境建立流程
        server_process = subprocess.Popen(
            [
                sys.executable, str(PROJECT_ROOT / "scripts" / "start_api_service.py"),
                "--config", str(config_path)
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8'
        )

        # --- 等待伺服器就緒 ---
        start_time = time.time()
        is_ready = False
        while time.time() - start_time < SERVER_START_TIMEOUT:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"伺服器提前崩潰。\nSTDOUT: {stdout}\nSTDERR: {stderr}")

            try:
                with httpx.Client() as client:
                    # 我們輪詢根 API，因為它最簡單，能最快確認服務是否啟動
                    response = client.get(f"http://127.0.0.1:{port}/", timeout=1)
                    if response.status_code == 200:
                        is_ready = True
                        break
            except httpx.RequestError:
                time.sleep(POLL_INTERVAL)

        if not is_ready:
            server_process.terminate()
            stdout, stderr = server_process.communicate()
            pytest.fail(f"伺服器在 {SERVER_START_TIMEOUT}s 內未能啟動。\nSTDOUT: {stdout}\nSTDERR: {stderr}")

        yield base_url

        # --- 清理 ---
        server_process.terminate()

def test_all_endpoints(live_server):
    """
    在一個測試中驗證所有端點，以避免重複啟動伺服器。
    """
    base_url = live_server

    # 測試 /
    response = httpx.get(base_url + "/")
    assert response.status_code == 200
    print("✅ 根端點 (/) 驗證成功。")

    # 測試 /api/v1/status/performance
    response = httpx.get(base_url + "/api/v1/status/performance")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_usage" in data
    print("✅ Performance endpoint 驗證成功。")

    # 測試 /api/v1/status/dashboard
    response = httpx.get(base_url + "/api/v1/status/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "current_stage" in data
    print("✅ Dashboard endpoint 驗證成功。")
