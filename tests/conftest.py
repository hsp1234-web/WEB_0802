# -*- coding: utf-8 -*-
# 檔案: tests/conftest.py
# 說明: Pytest 的公共測試配置文件。

import pytest
import sqlite3
from datetime import datetime, timezone

@pytest.fixture(scope="function")
def mock_db():
    """
    一個 pytest fixture，用於提供一個帶有模擬資料的記憶體 SQLite 資料庫。
    - scope="function": 確保每個測試函式都獲得一個乾淨、獨立的資料庫。
    """
    # 在記憶體中建立資料庫
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # --- 建立資料表 ---
    # 1. logs 表
    cursor.execute("""
    CREATE TABLE logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        level TEXT NOT NULL,
        source TEXT NOT NULL,
        message TEXT NOT NULL
    )
    """)

    # 2. status_updates 表
    cursor.execute("""
    CREATE TABLE status_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        key TEXT UNIQUE NOT NULL,
        value TEXT
    )
    """)

    # --- 插入模擬資料 ---
    now = datetime.now(timezone.utc)
    log_data = [
        (now, 'SUCCESS', 'DataProcessor', '資料處理成功，共 100 筆。'),
        (now, 'SUCCESS', 'DataProcessor', '資料處理成功，共 200 筆。'),
        (now, 'ERROR', 'APIConnector', 'API 連線失敗: timeout。'),
        (now, 'SUCCESS', 'DataProcessor', '資料處理成功，共 300 筆。'),
        (now, 'INFO', 'System', '系統啟動。'),
        (now, 'ERROR', 'Database', '資料庫寫入錯誤: disk full。'),
    ]
    cursor.executemany(
        "INSERT INTO logs (timestamp, level, source, message) VALUES (?, ?, ?, ?)",
        log_data
    )

    # 插入一個新鮮的心跳紀錄
    fresh_heartbeat_ts = now.isoformat()
    cursor.execute(
        "INSERT INTO status_updates (timestamp, key, value) VALUES (?, ?, ?)",
        (fresh_heartbeat_ts, 'system_heartbeat', 'OK')
    )

    conn.commit()

    # 將資料庫連線物件提供給測試函式
    yield conn

    # 測試結束後，關閉資料庫連線
    conn.close()


@pytest.fixture(scope="function")
def mock_report_files(tmp_path):
    """
    一個 pytest fixture，用於在臨時目錄中建立一組模擬的報告檔案。
    - scope="function": 確保每個測試函式都獲得一組乾淨的檔案。
    - 使用 pytest 內建的 tmp_path fixture 來處理臨時目錄的建立與清理。
    """
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    # 建立三個內容可預測的假報告檔案
    (reports_dir / "summary_report.md").write_text("這是總結報告。")
    (reports_dir / "detailed_log_report.md").write_text("這是詳細日誌報告。")
    (reports_dir / "performance_report.md").write_text("這是效能報告。")

    # yield 臨時目錄的路徑，供測試函式使用
    yield tmp_path


import subprocess
import sys
import os
import time
import socket
import shutil
from pathlib import Path

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
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")
    tmp_test_dir = PROJECT_ROOT / f"tmp_pytest_test_{worker_id}"

    # --- 設定環境 ---
    if tmp_test_dir.exists():
        shutil.rmtree(tmp_test_dir)
    tmp_test_dir.mkdir()

    python_executable = sys.executable
    port = find_free_port()
    config_path = tmp_test_dir / "config.json"

    # --- 啟動伺服器 ---
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
    yield {"port": port, "config_path": config_path, "base_url": f"http://127.0.0.1:{port}"}

    # --- 清理 ---
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    shutil.rmtree(tmp_test_dir)
