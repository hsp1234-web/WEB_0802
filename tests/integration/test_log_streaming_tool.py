# -*- coding: utf-8 -*-
"""
整合測試：Log Streaming Tool

這個測試模組負責驗證 `tools/log_streaming_tool.py` 的功能是否如預期般運作。
測試案例會啟動一個真實的日誌串流伺服器，並透過 WebSocket 與之互動。
"""
import subprocess
import json
import sys
import os
import time
import asyncio
import sqlite3
from pathlib import Path
import pytest
import websockets
from datetime import datetime, timezone

# --- 測試設定 ---
PROJECT_ROOT = Path(__file__).parent.parent.parent
TOOL_PATH = PROJECT_ROOT / "tools" / "log_streaming_tool.py"
VENV_DIR = PROJECT_ROOT / "tools" / ".venv_log_streaming_tool"
TEST_DB_DIR = PROJECT_ROOT / "tests/temp"
TEST_DB_PATH = TEST_DB_DIR / "test_log_streamer.db"
TEST_PORT = 8766

# --- 全域變數 ---
server_process = None

# --- 輔助函數 ---
def setup_test_database():
    """建立並初始化一個測試用的 SQLite 資料庫。"""
    TEST_DB_DIR.mkdir(exist_ok=True)
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        source TEXT
    )
    """)
    conn.commit()
    conn.close()

def write_log_to_db(level: str, message: str):
    """向測試資料庫寫入一筆日誌。"""
    conn = sqlite3.connect(TEST_DB_PATH)
    timestamp = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO logs (timestamp, level, message, source) VALUES (?, ?, ?, ?)",
        (timestamp, level, message, "test")
    )
    conn.commit()
    conn.close()

# --- Pytest Hooks (Setup/Teardown) ---
def setup_module(module):
    """在所有測試開始前執行的設定函數。"""
    global server_process

    # 1. 清理舊的虛擬環境和資料庫
    if VENV_DIR.exists():
        import shutil
        shutil.rmtree(VENV_DIR)

    # 2. 建立測試資料庫
    setup_test_database()

    # 3. 設定環境變數
    env = os.environ.copy()
    env["PHOENIX_DB_PATH"] = str(TEST_DB_PATH)
    env["LOG_STREAMER_PORT"] = str(TEST_PORT)

    # 4. 啟動伺服器子程序
    # 我們需要先執行一次工具來確保 venv 被建立
    print("\n--- 正在設定工具的虛擬環境... ---")
    setup_command = [sys.executable, str(TOOL_PATH), "--setup-only"]
    init_proc = subprocess.run(setup_command, capture_output=True, text=True, timeout=60, env=env)
    assert "環境設定完成" in init_proc.stderr, f"虛擬環境設定失敗: {init_proc.stderr}"

    print("--- 正在背景啟動日誌串流伺服器... ---")
    server_process = subprocess.Popen(
        [sys.executable, str(TOOL_PATH)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 5. 等待伺服器啟動
    time.sleep(3) # 給予足夠的時間讓伺服器啟動

    # 檢查伺服器是否正常運行
    assert server_process.poll() is None, f"伺服器啟動失敗，已退出。Stderr: {server_process.stderr.read()}"
    print("--- 伺服器已成功啟動。 ---")


def teardown_module(module):
    """在所有測試結束後執行的清理函數。"""
    print("\n--- 正在關閉日誌串流伺服器... ---")
    if server_process:
        server_process.terminate()
        # 為了偵錯，讀取並印出伺服器的 stderr
        try:
            stderr_output = server_process.stderr.read()
            print("\n--- Server Stderr Output ---")
            print(stderr_output)
            print("--------------------------\n")
        except Exception as e:
            print(f"無法讀取伺服器 stderr: {e}")

        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            print("--- 伺服器被強制終止。 ---")

    # 清理測試資料庫
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    if TEST_DB_DIR.exists():
        # 如果目錄為空，則刪除
        if not any(TEST_DB_DIR.iterdir()):
            TEST_DB_DIR.rmdir()


# --- 測試案例 ---

@pytest.mark.asyncio
async def test_log_streaming():
    """
    測試核心功能：
    1. 連接到 WebSocket 伺服器。
    2. 向資料庫寫入一筆新日誌。
    3. 驗證是否能從 WebSocket 收到這筆日誌。
    """
    uri = f"ws://localhost:{TEST_PORT}"

    try:
        async with websockets.connect(uri) as websocket:
            # 步驟 1: 清空可能在伺服器啟動期間產生的任何初始訊息
            try:
                await asyncio.wait_for(websocket.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                pass # 很好，沒有初始訊息

            # 步驟 2: 寫入一筆新的日誌到資料庫
            test_message = f"測試日誌訊息 @ {time.time()}"
            write_log_to_db("INFO", test_message)
            print(f"\n寫入測試日誌: '{test_message}'")

            # 步驟 3: 等待並接收來自伺服器的廣播
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"從 WebSocket 收到: {response}")

                # 驗證收到的資料
                logs = json.loads(response)
                assert isinstance(logs, list), "收到的資料應為一個列表"
                assert len(logs) > 0, "應至少收到一筆日誌"

                # 檢查最新的日誌是否是我們剛才寫入的
                latest_log = logs[-1]
                assert latest_log["level"] == "INFO"
                assert latest_log["message"] == test_message

            except asyncio.TimeoutError:
                pytest.fail("在5秒內沒有從 WebSocket 收到任何訊息。")

    except ConnectionRefusedError:
        pytest.fail("無法連接到 WebSocket 伺服器，請檢查伺服器是否正常啟動。")
