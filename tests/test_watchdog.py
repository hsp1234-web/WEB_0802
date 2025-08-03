# -*- coding: utf-8 -*-
# 檔案: tests/test_watchdog.py
# 說明: 對 src/phoenix_core/watchdog.py 中的函式進行單元測試。

import pytest
import sqlite3
from datetime import datetime, timedelta, timezone
from src.phoenix_core.watchdog import check_heartbeat_status, HEARTBEAT_KEY

def test_heartbeat_ok(mock_db):
    """
    測試正常的心跳。
    使用 mock_db 中預設的、新鮮的時間戳，函式應返回 'OK'。
    """
    # 使用一個合理的閾值，例如 15 秒
    status = check_heartbeat_status(mock_db, threshold_seconds=15)
    assert status == 'OK'

def test_heartbeat_expired(mock_db):
    """
    測試過期的心跳。
    我們將手動更新資料庫中的時間戳，使其過期。
    """
    # 1. 將心跳時間戳設定為 61 秒前
    expired_ts = (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat()

    cursor = mock_db.cursor()
    cursor.execute(
        "UPDATE status_updates SET timestamp = ? WHERE key = ?",
        (expired_ts, HEARTBEAT_KEY)
    )
    mock_db.commit()

    # 2. 使用 60 秒的閾值進行檢查
    # 因為時間戳是 61 秒前，所以應該被判定為 'STOPPED'
    status = check_heartbeat_status(mock_db, threshold_seconds=60)

    # 3. 斷言結果
    assert status == 'STOPPED'

def test_heartbeat_not_found(mock_db):
    """
    測試當心跳紀錄不存在時的情況。
    """
    # 刪除心跳紀錄
    cursor = mock_db.cursor()
    cursor.execute("DELETE FROM status_updates WHERE key = ?", (HEARTBEAT_KEY,))
    mock_db.commit()

    status = check_heartbeat_status(mock_db, threshold_seconds=15)
    assert status == 'NOT_FOUND'
