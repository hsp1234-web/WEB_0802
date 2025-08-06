# -*- coding: utf-8 -*-
# 檔案: scripts/heartbeat_worker.py
# 說明: 一個獨立的背景工作者，專門負責向資料庫寫入心跳訊號。

import sys
import time
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

def main():
    """主執行函數"""
    # --- Step 1: 設定路徑 ---
    # 確保我們可以從 src 目錄導入模組
    try:
        project_root = Path(__file__).resolve().parents[1]
        sys.path.append(str(project_root))
        from src.phoenix_core.database import DatabaseManager
    except ImportError as e:
        # 如果發生導入錯誤，這是一個嚴重問題，直接印出到 stdout
        # 因為日誌重導向可能已設定，所以直接寫入檔案可能更可靠
        # 但在此最簡化版本中，我們先嘗試 print
        print(f"FATAL: Failed to import DatabaseManager: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Step 2: 初始化 ---
    worker_name = "heartbeat_worker"
    interval_seconds = 5
    heartbeat_key = "last_heartbeat"

    print(f"[{worker_name}] 心跳工作者啟動。每 {interval_seconds} 秒更新一次心跳。")

    try:
        db_manager = DatabaseManager(db_path=str(project_root / "storage/state.db"))
        db_manager._blocking_initialize()
    except Exception as e:
        print(f"FATAL: Failed to initialize DatabaseManager: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Step 3: 主迴圈 ---
    while True:
        try:
            # 使用 timezone.utc 替代 pytz
            timestamp_str = datetime.now(timezone.utc).isoformat()
            db_manager.write_status_update(heartbeat_key, timestamp_str)
            print(f"[{worker_name}] Heartbeat updated: {timestamp_str}")

        except sqlite3.Error as e:
            print(f"[{worker_name}] Database error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[{worker_name}] Unexpected error: {e}", file=sys.stderr)

        time.sleep(interval_seconds)

if __name__ == "__main__":
    main()
