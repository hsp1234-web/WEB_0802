# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/db_queries.py
# 說明: 此模組包含與資料庫互動的可重用查詢函式。

import sqlite3

def query_logs_by_level(conn: sqlite3.Connection, level: str, limit: int = 10) -> list:
    """
    根據指定的日誌等級查詢日誌紀錄。

    Args:
        conn (sqlite3.Connection): 資料庫連線物件。
        level (str): 要查詢的日誌等級 (例如 'SUCCESS', 'ERROR')。
        limit (int): 返回的最大紀錄數量。

    Returns:
        list: 包含查詢結果的元組列表。
    """
    cursor = conn.cursor()
    query = """
        SELECT id, timestamp, level, source, message
        FROM logs
        WHERE level = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    cursor.execute(query, (level, limit))
    return cursor.fetchall()

def query_logs_by_levels(conn: sqlite3.Connection, levels: list[str], limit: int = 50) -> list:
    """
    根據指定的日誌等級列表查詢日誌紀錄。

    Args:
        conn (sqlite3.Connection): 資料庫連線物件。
        levels (list[str]): 要查詢的日誌等級列表 (例如 ['SUCCESS', 'ERROR'])。
        limit (int): 返回的最大紀錄數量。

    Returns:
        list: 包含查詢結果的元組列表。
    """
    if not levels:
        return []

    cursor = conn.cursor()
    # 使用 IN 子句和 '?' 佔位符來安全地查詢多個等級
    placeholders = ','.join('?' for _ in levels)
    query = f"""
        SELECT id, timestamp, level, source, message
        FROM logs
        WHERE level IN ({placeholders})
        ORDER BY timestamp DESC
        LIMIT ?
    """
    # 將 limit 作為最後一個參數傳入
    params = levels + [limit]
    cursor.execute(query, params)
    return cursor.fetchall()
