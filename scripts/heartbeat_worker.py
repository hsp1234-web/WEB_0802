# -*- coding: utf-8 -*-
# 檔案: scripts/heartbeat_worker.py
# 說明: 一個獨立的背景工作者，專門負責向資料庫寫入心跳訊號。

import sys
import time
import sqlite3
from datetime import datetime
import pytz
from pathlib import Path

# 將專案根目錄添加到 sys.path，以便能夠導入 phoenix_core
# 假設此腳本是從專案根目錄執行的
# 使用 Path(__file__).resolve().parents[1] 來獲取專案根目錄
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from src.phoenix_core.database import DatabaseManager

HEARTBEAT_INTERVAL_SECONDS = 5
HEARTBEAT_KEY = "last_heartbeat"
WORKER_NAME = "heartbeat_worker"

def run_heartbeat():
    """
    執行心跳迴圈，定期更新資料庫中的狀態。
    """
    print(f"[{WORKER_NAME}] 心跳工作者啟動。每 {HEARTBEAT_INTERVAL_SECONDS} 秒更新一次心跳。")

    # 注意：由於這是一個獨立的腳本，我們直接實例化 DatabaseManager
    # 或者，如果我們想要與主應用程式共享完全相同的實例和設定，
    # 我們需要確保初始化方式一致。
    # 在此，我們使用預設路徑，這與 `local_run.py` 的預期行為一致。
    db_manager = DatabaseManager(db_path=str(project_root / "storage/state.db"))

    # 執行一次初始化的檢查，確保資料表存在
    # 在一個獨立的腳本中，我們需要手動調用它
    # 使用 blocking_initialize 因為這是在啟動時，非同步事件迴圈外
    db_manager._blocking_initialize()

    while True:
        try:
            current_time_utc = datetime.now(pytz.utc)
            timestamp_str = current_time_utc.isoformat()

            # 使用 DatabaseManager 的 write_status_update 方法
            # 這確保了日誌記錄和資料庫更新的邏輯是集中的
            db_manager.write_status_update(HEARTBEAT_KEY, timestamp_str)

            print(f"[{WORKER_NAME}] 心跳已更新: {timestamp_str}")

        except sqlite3.Error as e:
            print(f"[{WORKER_NAME}] 資料庫錯誤: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[{WORKER_NAME}] 發生未預期的錯誤: {e}", file=sys.stderr)

        time.sleep(HEARTBEAT_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_heartbeat()
