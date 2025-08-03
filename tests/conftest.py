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
