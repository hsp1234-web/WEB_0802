#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日誌串流獨立工具 (Log Streaming Tool)

功能:
1.  自我管理虛擬環境和依賴 (`websockets`, `pytz`)。
2.  從環境變數讀取設定 (資料庫路徑, WebSocket 埠號)。
3.  啟動一個獨立的 WebSocket 伺服器。
4.  定期從 SQLite 資料庫讀取新的日誌記錄。
5.  將新的日誌即時廣播給所有連接的 WebSocket 客戶端。
"""
import os
import sys
import subprocess
import venv
import time
import json
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# --- 設定 ---
TOOL_NAME = "LogStreamingTool"
VENV_DIR = Path(__file__).parent / f".venv_{Path(__file__).stem}"
DB_PATH_ENV = "PHOENIX_DB_PATH"
DEFAULT_DB_PATH = "storage/state.db"
PORT_ENV = "LOG_STREAMER_PORT"
DEFAULT_PORT = 8765
POLL_INTERVAL = 1.5  # 秒

# --- 依賴列表 ---
DEPENDENCIES = {
    "websockets": "websockets==12.0",
    "pytz": "pytz==2024.1", # database.py 使用 pytz
}

# --- 全域變數 ---
# 用於儲存所有已連接的客戶端
CONNECTED_CLIENTS = set()

# --- 日誌記錄 ---
def log(message):
    """將日誌訊息寫入標準錯誤流。"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}][{TOOL_NAME}] {message}", file=sys.stderr)

# --- 環境設定 ---
def setup_environment():
    """設定虛擬環境並安裝依賴。"""
    if VENV_DIR.exists() and (VENV_DIR / ".tool_setup_complete").exists():
        return

    log("🚀 開始環境設定...")
    if not VENV_DIR.exists():
        log(f"正在建立虛擬環境於: {VENV_DIR}")
        venv.create(VENV_DIR, with_pip=True)

    pip_executable = VENV_DIR / "bin" / "pip" if os.name != "nt" else VENV_DIR / "Scripts" / "pip.exe"

    log("📦 正在檢查並安裝依賴...")
    try:
        requirements = [spec for spec in DEPENDENCIES.values()]
        subprocess.check_call([str(pip_executable), "install", *requirements], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        log("✅ 所有依賴均已準備就緒。")
    except subprocess.CalledProcessError as e:
        log(f"❌ 依賴安裝失敗。錯誤: {e.stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)

    (VENV_DIR / ".tool_setup_complete").touch()

def activate_venv():
    """啟動虛擬環境，將其路徑加入到 sys.path。"""
    if not VENV_DIR.exists():
        sys.exit(f"❌ 虛擬環境目錄不存在: {VENV_DIR}")

    site_packages = VENV_DIR / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if os.name == 'nt':
        site_packages = VENV_DIR / "Lib" / "site-packages"

    if not site_packages.exists():
        sys.exit(f"❌ 找不到 site-packages 目錄: {site_packages}")

    sys.path.insert(0, str(site_packages))

# --- WebSocket 伺服器邏輯 ---
async def handler(websocket):
    """處理個別 WebSocket 連線。"""
    log(f"ℹ️ 新的客戶端已連接: {websocket.remote_address}")
    CONNECTED_CLIENTS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        log(f"ℹ️ 客戶端已斷開連接: {websocket.remote_address}")
        CONNECTED_CLIENTS.remove(websocket)

async def broadcast(message: str):
    """向所有已連接的客戶端廣播訊息。"""
    if CONNECTED_CLIENTS:
        # 使用 asyncio.gather 是執行多個協程的現代、推薦方式。
        # 它會將協程包裝成任務並發執行。
        tasks = [client.send(message) for client in CONNECTED_CLIENTS]
        await asyncio.gather(*tasks)

async def log_polling_task(db_path: Path):
    """定期從資料庫拉取日誌並廣播。"""
    log("📡 日誌輪詢任務已啟動...")
    # 將初始檢查時間設定為一個遙遠的過去，以確保第一次輪詢能獲取到所有現存日誌，避免啟動時的競爭條件。
    last_check_time = datetime(2000, 1, 1, tzinfo=timezone.utc)

    while True:
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            timestamp_str = last_check_time.isoformat()
            cursor.execute(
                "SELECT timestamp, level, message FROM logs WHERE timestamp > ? ORDER BY timestamp ASC",
                (timestamp_str,)
            )
            rows = cursor.fetchall()
            conn.close()

            log(f"🔍 查詢到 {len(rows)} 筆新日誌。")

            if rows:
                logs = [dict(row) for row in rows]
                last_check_time = datetime.fromisoformat(logs[-1]['timestamp'])
                await broadcast(json.dumps(logs))
                log(f"📤 已廣播 {len(logs)} 條新日誌。")

        except sqlite3.Error as e:
            log(f"❌ 資料庫查詢錯誤: {e}")
        except Exception as e:
            log(f"❌ 輪詢任務發生未知錯誤: {e}")

        await asyncio.sleep(POLL_INTERVAL)

async def main():
    """主執行函數。"""
    log("--- 日誌串流工具已啟動 ---")

    # 讀取設定
    db_path_str = os.getenv(DB_PATH_ENV, DEFAULT_DB_PATH)
    db_path = Path(db_path_str)
    port = int(os.getenv(PORT_ENV, DEFAULT_PORT))

    log(f"🔍 資料庫路徑: {db_path.resolve()}")
    log(f"🔌 WebSocket 伺服器將監聽於: 0.0.0.0:{port}")

    if not db_path.exists():
        log(f"⚠️ 警告: 資料庫檔案不存在。將會等待它被主應用程式建立。")

    # 匯入 websockets
    try:
        import websockets
    except ImportError:
        log("❌ 錯誤：`websockets` 函式庫未安裝或不在 sys.path 中。")
        sys.exit(1)

    # 啟動日誌輪詢背景任務
    asyncio.create_task(log_polling_task(db_path))

    # 啟動 WebSocket 伺服器
    server = await websockets.serve(handler, "0.0.0.0", port)
    log("✅ WebSocket 伺服器已成功啟動。")

    await server.wait_closed()

if __name__ == "__main__":
    if "--setup-only" in sys.argv:
        log("💡 偵測到 --setup-only 參數，僅執行環境設定...")
        setup_environment()
        log("✅ 環境設定完成。")
        sys.exit(0)

    # 正常執行流程
    # 1. 設定環境
    setup_environment()
    activate_venv()

    # 2. 執行主程式
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n--- 收到退出訊號，正在關閉伺服器... ---")
    except Exception as e:
        log(f"❌ 伺服器發生致命錯誤: {e}")
        sys.exit(1)

    log("--- 日誌串流工具已關閉 ---")
