# -*- coding: utf-8 -*-
# 檔案: tests/integration/test_log_filtering.py
# 說明: 驗證後端 API 是否能根據 config.json 正確過濾日誌。

import subprocess
import sys
import os
import time
import json
import httpx
from pathlib import Path
import pytest
import socket
import shutil

# --- 測試設定 ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def find_free_port() -> int:
    """找到一個可用的埠號"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

@pytest.fixture(scope="module")
def live_server(request):
    """
    (Fixture) 啟動一個真實的後端 API 伺服器以供測試。
    這個 fixture 會處理啟動和關閉伺服器的整個生命週期。
    使用 worker_id 確保在並行測試中每個 worker 有獨立的臨時目錄。
    """
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")
    tmp_test_dir = PROJECT_ROOT / f"tmp_log_filter_test_{worker_id}"

    # --- 設定環境 ---
    if tmp_test_dir.exists():
        shutil.rmtree(tmp_test_dir)
    tmp_test_dir.mkdir()

    # 使用當前正在執行 pytest 的 Python 直譯器，這樣更具可移植性
    python_executable = sys.executable
    if not Path(python_executable).exists():
        pytest.fail(f"無法找到 Python 直譯器: {python_executable}")

    port = find_free_port()
    config_path = tmp_test_dir / "config.json"

    # --- 啟動伺服器 ---
    # 將設定檔路徑和 PYTHONPATH 透過環境變數傳遞
    test_env = os.environ.copy()
    test_env["PHOENIX_CONFIG_PATH"] = str(config_path)
    test_env["PYTHONPATH"] = str(PROJECT_ROOT)

    command = [
        str(python_executable), "-m", "uvicorn",
        "src.phoenix_core.main:app",
        "--host", "0.0.0.0",
        "--port", str(port)
    ]

    server_process = subprocess.Popen(command, env=test_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 等待伺服器就緒
    is_ready = False
    for _ in range(20): # 等待最多 10 秒
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                is_ready = True
                break
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(0.5)

    if not is_ready:
        server_process.kill()
        pytest.fail(f"伺服器在埠號 {port} 上未能於 10 秒內啟動。")

    # --- 將伺服器資訊傳遞給測試 ---
    yield {"port": port, "config_path": config_path}

    # --- 清理 ---
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    shutil.rmtree(tmp_test_dir)

def create_config(path: Path, log_levels: dict):
    """建立一個測試用的 config.json 檔案"""
    config = {
        "log_settings": {
            "levels": log_levels
        }
    }
    with open(path, "w") as f:
        json.dump(config, f)

@pytest.mark.parametrize("enabled_levels, expected_levels", [
    (
        {"INFO": True, "SUCCESS": False, "ERROR": True, "BATTLE": False, "CMD": False},
        {"INFO", "ERROR"}
    ),
    (
        {"INFO": True, "SUCCESS": True, "ERROR": True, "BATTLE": True, "CMD": True},
        {"INFO", "SUCCESS", "ERROR", "BATTLE", "CMD"}
    ),
    (
        {"INFO": False, "SUCCESS": False, "ERROR": False, "BATTLE": False, "CMD": False},
        set()
    ),
    (
        {"BATTLE": True}, # 只啟用一個
        {"BATTLE"}
    )
])
def test_log_filtering(live_server, enabled_levels, expected_levels):
    """
    測試 API 是否根據 config.json 中的設定正確過濾日誌。
    """
    port = live_server["port"]
    config_path = live_server["config_path"]

    # 1. 根據測試參數建立設定檔
    create_config(config_path, enabled_levels)

    # 2. 呼叫 API 端點
    # 需要給伺服器一點時間來重新載入檔案，雖然 uvicorn 不會自動重載 json，
    # 但我們的 API 每次請求都會讀取檔案，所以直接請求即可。
    time.sleep(0.1)
    api_url = f"http://127.0.0.1:{port}/api/v1/status/dashboard"
    try:
        response = httpx.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except (httpx.RequestError, json.JSONDecodeError) as e:
        pytest.fail(f"API 請求失敗: {e}")

    # 3. 驗證回傳的日誌
    assert "logs" in data, "API 回應中缺少 'logs' 欄位"

    returned_levels = {log["level"] for log in data["logs"]}

    assert returned_levels == expected_levels, \
        f"日誌過濾不正確！預期看到 {expected_levels}，但實際看到 {returned_levels}"
