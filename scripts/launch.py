# 檔案: scripts/launch.py
# 說明: 專案的核心後端服務，內建 API 伺服器，負責執行任務並提供狀態更新。
# 作者: Jules
# 版本: V23.API

import sqlite3
import time
import subprocess
import sys
import os
import asyncio
import logging
import json
import psutil
import argparse
from pathlib import Path
from aiohttp import web
from collections import deque

# --- 全域設定 (可由環境變數覆寫) ---
DB_PATH = Path(os.environ.get("PHOENIX_DB_PATH", "state.db"))
LOG_PATH = Path(os.environ.get("PHOENIX_LOG_PATH", "uvicorn.log"))
API_HOST = "localhost"
API_PORT = 8088

# --- 設定日誌 (可由設定檔覆寫) ---
def setup_logging(config=None):
    """根據設定檔設定日誌系統。"""
    # 步驟 1: 清理舊的日誌檔案 (如果存在)
    # 必須在設定 basicConfig 之前完成
    if LOG_PATH.exists():
        os.remove(LOG_PATH)

    # 步驟 2: 決定日誌等級
    log_level = logging.INFO
    if config and 'log_level' in config:
        level_name = config['log_level'].upper()
        log_level = getattr(logging, level_name, logging.INFO)
        print(f"日誌等級設定為: {level_name}")

    # 步驟 3: 設定 basicConfig
    # 移除現有的 handlers，以防重複設定
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_PATH, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger()

log = setup_logging() # 使用預設值初始化

# --- 狀態管理 ---
# 使用一個集中的字典來管理共享狀態，這樣更清晰且易於存取。
shared_state = {
    "current_stage": "初始化中...",
    "cpu_usage": 0.0,
    "ram_usage": 0.0,
    "apps_status": {}, # 模擬的微服務狀態
    "logs": deque(maxlen=100), # 只保留最新的 100 筆日誌在記憶體中
    "shutdown_event": asyncio.Event(),
    "db_conn": None
}

# --- 資料庫管理 (同步操作) ---
def setup_database(db_path):
    """建立資料庫和 status 表格。"""
    log.info(f"正在設定資料庫於: {db_path}")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS status (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            timestamp TEXT,
            level TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    log.info("資料庫表格 'status' 和 'logs' 已確認存在。")
    return conn

def persist_status_to_db(conn, key, value):
    """將單一鍵值對持久化到資料庫。"""
    try:
        cursor = conn.cursor()
        # 使用 TEXT 類型儲存 JSON 字串
        value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        cursor.execute("INSERT OR REPLACE INTO status (key, value) VALUES (?, ?)", (key, value_str))
        conn.commit()
    except Exception as e:
        log.error(f"寫入資料庫時發生錯誤 (key: {key}): {e}")

def persist_final_state(conn):
    """在關機前將最終狀態寫入資料庫。"""
    log.info("正在將最終狀態持久化到資料庫...")
    persist_status_to_db(conn, "final_stage", shared_state["current_stage"])
    persist_status_to_db(conn, "final_apps_status", shared_state["apps_status"])

    # 將記憶體中的日誌寫入資料庫
    try:
        cursor = conn.cursor()
        log_entries = [
            (log_entry['timestamp'], log_entry['level'], log_entry['message'])
            for log_entry in shared_state['logs']
        ]
        cursor.executemany("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)", log_entries)
        conn.commit()
        log.info(f"已成功將 {len(log_entries)} 筆日誌寫入資料庫。")
    except Exception as e:
        log.error(f"將日誌寫入資料庫時發生錯誤: {e}")


# --- API 端點處理器 ---
async def get_status_handler(request):
    """
    處理 /api/v1/status 請求。
    從共享狀態中讀取數據，並以 JSON 格式返回。
    """
    status_payload = {
        "status": {
            "current_stage": shared_state["current_stage"],
            "cpu_usage": shared_state["cpu_usage"],
            "ram_usage": shared_state["ram_usage"],
            # 將 apps_status 字典轉換為 JSON 字串以符合原始設計
            "apps_status": json.dumps(shared_state["apps_status"]),
            # 模擬 action_url，因為這部分是由 Colab 生成的
            "action_url": None
        },
        # 將 deque 轉換為 list 以便 JSON 序列化
        "logs": list(shared_state["logs"])
    }
    return web.json_response(status_payload)

async def shutdown_handler(request):
    """處理 /api/v1/shutdown 請求，觸發優雅關機。"""
    log.info("接收到來自 API 的關機信號。")
    shared_state["shutdown_event"].set()
    return web.Response(text="Shutdown signal received. The application will now terminate gracefully.")

# --- 背景任務 ---
async def monitor_resources():
    """一個獨立的任務，定期更新硬體資源使用率。"""
    log.info("資源監控任務已啟動。")
    while not shared_state["shutdown_event"].is_set():
        shared_state["cpu_usage"] = psutil.cpu_percent(interval=None)
        shared_state["ram_usage"] = psutil.virtual_memory().percent
        await asyncio.sleep(2) # 每 2 秒更新一次
    log.info("資源監控任務已停止。")

def update_stage(stage_name, message=None):
    """輔助函式，用於更新當前階段並記錄日誌。"""
    shared_state["current_stage"] = stage_name
    log_message = message or stage_name
    log.info(log_message)
    shared_state["logs"].append({
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "message": log_message
    })


async def core_task():
    """
    主要的業務邏輯，現在是一個非同步的背景任務。
    """
    try:
        update_stage("核心任務：啟動中")
        shared_state["apps_status"] = {"database": "starting", "cache": "pending"}
        await asyncio.sleep(2)

        update_stage("核心任務：正在設定服務", "核心任務：正在設定服務 (Database)")
        shared_state["apps_status"]["database"] = "running"
        shared_state["apps_status"]["cache"] = "starting"
        await asyncio.sleep(2)

        update_stage("核心任務：正在處理數據", "核心任務：正在處理數據 (Cache)")
        shared_state["apps_status"]["cache"] = "running"
        await asyncio.sleep(3)

        update_stage("核心任務：處理完畢", "所有核心任務已成功處理完畢。")

    except asyncio.CancelledError:
        log.warning("核心任務被取消。")
        update_stage("任務被取消")
    except Exception as e:
        log.error(f"核心任務發生錯誤: {e}", exc_info=True)
        update_stage("任務失敗", f"核心任務執行失敗: {e}")
    finally:
        # 核心任務結束後，觸發關機事件，讓整個應用程式退出
        log.info("核心任務執行流程結束，觸發應用程式關機。")
        shared_state["shutdown_event"].set()


# --- 主應用程式設定與執行 ---
async def main(config=None):
    """設定並執行 aiohttp 應用程式和背景任務。"""
    global log
    # 如果有設定檔，重新設定日誌
    if config:
        log = setup_logging(config)

    log.debug("這是一條 DEBUG 訊息，用來驗證日誌等級設定。")

    # 清理舊的資料庫檔案
    if DB_PATH.exists():
        os.remove(DB_PATH)
        log.info(f"已刪除舊的資料庫檔案: {DB_PATH}")

    # 初始化資料庫
    shared_state["db_conn"] = setup_database(DB_PATH)
    update_stage("後端 API 服務已啟動")

    # 建立 aiohttp 應用
    app = web.Application()
    app.add_routes([
        web.get('/api/v1/status', get_status_handler),
        web.post('/api/v1/shutdown', shutdown_handler),
    ])

    # 啟動背景任務
    resource_monitor_task = asyncio.create_task(monitor_resources())
    main_core_task = asyncio.create_task(core_task())

    # 設定 web runner
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, API_HOST, API_PORT)
    await site.start()
    log.info(f"🚀 API 伺服器正在 http://{API_HOST}:{API_PORT} 上運行")

    # 等待關機信號
    await shared_state["shutdown_event"].wait()

    # --- 優雅關機程序 ---
    log.info("開始執行優雅關機程序...")
    update_stage("關機中...")

    # 停止 aiohttp 伺服器
    await runner.cleanup()
    log.info("API 伺服器已停止。")

    # 取消背景任務
    resource_monitor_task.cancel()
    main_core_task.cancel()
    await asyncio.gather(resource_monitor_task, main_core_task, return_exceptions=True)
    log.info("所有背景任務已清理完畢。")

    # 將最終狀態寫入資料庫
    persist_final_state(shared_state["db_conn"])

    # 關閉資料庫連線
    if shared_state["db_conn"]:
        shared_state["db_conn"].close()
        log.info("資料庫連線已關閉。")

    # --- 任務結束後，呼叫報告生成器 ---
    # 由於我們現在是 API 服務，報告應該由另一個程序觸發，
    # 但根據原始需求，我們仍然在這裡呼叫它。
    # 在一個真正的微服務架構中，這一步會被移除。
    log.info("準備生成最終報告...")
    try:
        report_script_path = Path(__file__).parent / "report_generator.py"
        if report_script_path.exists():
            result = subprocess.run(
                [
                    sys.executable,
                    str(report_script_path),
                    "--db-file", str(DB_PATH),
                    "--report-dir", str(DB_PATH.parent / "reports")
                ],
                check=True, capture_output=True, text=True, encoding='utf-8'
            )
            log.info("報告生成成功。")
        else:
            log.warning(f"找不到報告生成腳本 {report_script_path}，跳過報告生成。")
    except subprocess.CalledProcessError as e:
        log.error(f"報告生成腳本執行失敗: {e.stderr}")

    log.info("launch.py 執行完畢。")

if __name__ == "__main__":
    # 設定命令列參數解析
    parser = argparse.ArgumentParser(description="V23 後端 API 伺服器")
    parser.add_argument("--config", type=Path, help="指向 JSON 設定檔的路徑。")
    args = parser.parse_args()

    config_data = None
    if args.config and args.config.exists():
        print(f"正在從 {args.config} 載入設定...")
        with open(args.config, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    elif args.config:
        print(f"警告: 找不到設定檔 {args.config}，將使用預設設定。")

    # 為了在 Windows 上良好運作，需要設定事件迴圈策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 匯入 datetime 以便在 update_stage 中使用
    from datetime import datetime

    try:
        asyncio.run(main(config=config_data))
    except KeyboardInterrupt:
        # log 可能尚未被完全設定，所以用 print
        print("偵測到手動中斷 (Ctrl+C)，程式正在終止。")
