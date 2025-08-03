# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/watchdog.py
# 說明: 此模組提供心跳偵測 (看門狗) 相關的功能。

import sqlite3
from datetime import datetime, timezone

HEARTBEAT_KEY = "system_heartbeat"
HEARTBEAT_TABLE = "status_updates"

def check_heartbeat_status(conn: sqlite3.Connection, threshold_seconds: int) -> str:
    """
    檢查資料庫中的系統心跳時間戳，判斷其是否在指定的秒數內。

    Args:
        conn (sqlite3.Connection): 資料庫連線物件。
        threshold_seconds (int): 心跳被視為過期的秒數閾值。

    Returns:
        str: 'OK' 表示心跳正常，'NOT_FOUND' 表示找不到紀錄，'STOPPED' 表示心跳已過期。
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT timestamp FROM {HEARTBEAT_TABLE} WHERE key = ?", (HEARTBEAT_KEY,)
        )
        result = cursor.fetchone()

        if result is None:
            return 'NOT_FOUND'

        last_heartbeat_str = result[0]

        # 處理與 ISO 8601 格式相容的時間字串 (可能包含 Z 或時區)
        try:
            if 'Z' in last_heartbeat_str or '+' in last_heartbeat_str:
                 last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
            else:
                 # 若無時區資訊，則假定為 UTC
                 last_heartbeat = datetime.fromisoformat(last_heartbeat_str).replace(tzinfo=timezone.utc)
        except ValueError:
             # 向下相容舊的格式
            last_heartbeat = datetime.strptime(last_heartbeat_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        time_diff = (now_utc - last_heartbeat).total_seconds()

        if time_diff > threshold_seconds:
            return 'STOPPED'

        return 'OK'

    except sqlite3.Error as e:
        # 在測試環境中，我們希望錯誤能被拋出以供調試
        print(f"資料庫錯誤: {e}")
        raise
