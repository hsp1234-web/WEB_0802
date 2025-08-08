#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日誌串流獨立工具 (Log Streaming Tool) - v2 (烘烤模式)

功能:
1.  啟動時檢查並解壓縮預烘烤的虛擬環境。
2.  將依賴 (`websockets`, `pytz`) 加入 sys.path。
3.  在單一進程中啟動 WebSocket 伺服器。
4.  定期從 SQLite 資料庫讀取並廣播日誌。
"""
import os
import sys
import time
import json
import asyncio
import sqlite3
import tarfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

# --- 設定 ---
TOOL_NAME = "LogStreamingTool"
VENV_DIR = Path(__file__).parent / f".venv_{Path(__file__).stem}"
BAKED_ENV_ARCHIVE = Path(__file__).parent.parent / "storage" / "baked_envs" / f"{VENV_DIR.name}.tar.xz"

DB_PATH_ENV = "PHOENIX_DB_PATH"
DEFAULT_DB_PATH = "storage/state.db"
PORT_ENV = "LOG_STREAMER_PORT"
DEFAULT_PORT = 8765
POLL_INTERVAL = 1.5

# --- 依賴列表 (僅供參考) ---
DEPENDENCIES = {
    "websockets": "websockets==12.0",
    "pytz": "pytz==2024.1",
}

# --- 全域變數 ---
CONNECTED_CLIENTS = set()

# --- 日誌記錄 ---
def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}][{TOOL_NAME}] {message}", file=sys.stderr)

# --- 環境準備 ---
def prepare_environment():
    if VENV_DIR.exists():
        log(f"✅ 虛擬環境 '{VENV_DIR.name}' 已存在。")
        return
    log(f"🔍 虛擬環境 '{VENV_DIR.name}' 不存在，正在尋找預烘烤的存檔...")
    if not BAKED_ENV_ARCHIVE.exists():
        log(f"❌ 嚴重錯誤：找不到預烘烤的環境存檔: {BAKED_ENV_ARCHIVE}")
        log("   請先執行 'python scripts/bake_tool_envs.py' 來建立環境存檔。")
        sys.exit(1)
    log(f"📦 找到存檔，正在解壓縮至 '{VENV_DIR.parent}' (使用 xz)...")
    try:
        with tarfile.open(BAKED_ENV_ARCHIVE, "r:xz") as tar:
            tar.extractall(path=VENV_DIR.parent)
        log("✅ 環境解壓縮成功。")
    except Exception as e:
        log(f"❌ 解壓縮環境時發生錯誤: {e}")
        if VENV_DIR.exists():
            shutil.rmtree(VENV_DIR)
        sys.exit(1)

def activate_venv():
    site_packages = VENV_DIR / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if os.name == 'nt':
        site_packages = VENV_DIR / "Lib" / "site-packages"
    if not site_packages.exists():
        log(f"❌ 嚴重錯誤：在虛擬環境中找不到 site-packages 目錄: {site_packages}")
        sys.exit(1)
    log(f"🔌 正在將 '{site_packages}' 加入到 sys.path")
    sys.path.insert(0, str(site_packages))

# --- WebSocket 伺服器邏輯 ---
async def handler(websocket):
    log(f"ℹ️ 新的客戶端已連接: {websocket.remote_address}")
    CONNECTED_CLIENTS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        log(f"ℹ️ 客戶端已斷開連接: {websocket.remote_address}")
        CONNECTED_CLIENTS.remove(websocket)

async def broadcast(message: str):
    if CONNECTED_CLIENTS:
        tasks = [client.send(message) for client in CONNECTED_CLIENTS]
        await asyncio.gather(*tasks)

async def log_polling_task(db_path: Path):
    log("📡 日誌輪詢任務已啟動...")
    last_check_time = datetime(2000, 1, 1, tzinfo=timezone.utc)
    while True:
        try:
            if not db_path.exists():
                await asyncio.sleep(POLL_INTERVAL)
                continue

            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            timestamp_str = last_check_time.isoformat()
            cursor.execute("SELECT timestamp, level, message FROM logs WHERE timestamp > ? ORDER BY timestamp ASC", (timestamp_str,))
            rows = cursor.fetchall()
            conn.close()

            if rows:
                logs = [dict(row) for row in rows]
                last_check_time = datetime.fromisoformat(logs[-1]['timestamp'])
                await broadcast(json.dumps(logs))
                log(f"📤 已廣播 {len(logs)} 條新日誌。")
        except sqlite3.OperationalError as e:
             if "database is locked" in str(e):
                log("⚠️ 資料庫被鎖定，將在下一輪重試。")
             else:
                log(f"❌ 資料庫查詢錯誤: {e}")
        except Exception as e:
            log(f"❌ 輪詢任務發生未知錯誤: {e}")
        await asyncio.sleep(POLL_INTERVAL)

async def start_server():
    """啟動 WebSocket 伺服器和輪詢任務。"""
    db_path_str = os.getenv(DB_PATH_ENV, DEFAULT_DB_PATH)
    db_path = Path(db_path_str)
    port = int(os.getenv(PORT_ENV, DEFAULT_PORT))

    log(f"🔍 資料庫路徑: {db_path.resolve()}")
    log(f"🔌 WebSocket 伺服器將監聽於: 0.0.0.0:{port}")

    # 匯入 websockets
    try:
        import websockets
    except ImportError:
        log("❌ 錯誤：`websockets` 函式庫未安裝或不在 sys.path 中。")
        log("   請確認虛擬環境已正確啟動。")
        sys.exit(1)

    polling_task = asyncio.create_task(log_polling_task(db_path))
    server = await websockets.serve(handler, "0.0.0.0", port)

    log("✅ WebSocket 伺服器已成功啟動。")
    await server.wait_closed()
    polling_task.cancel() # 確保任務被清理
    try:
        await polling_task
    except asyncio.CancelledError:
        log("ℹ️ 日誌輪詢任務已取消。")


def main():
    log("--- 日誌串流工具已啟動 (v2 烘烤模式) ---")

    # 1. 準備並啟動環境
    prepare_environment()
    activate_venv()

    # 2. 執行主程式
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        log("\n--- 收到退出訊號，正在關閉伺服器... ---")
    except Exception as e:
        log(f"❌ 伺服器發生致命錯誤: {e}")
        sys.exit(1)

    log("--- 日誌串流工具已關閉 ---")

if __name__ == "__main__":
    main()
