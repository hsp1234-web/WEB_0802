# -*- coding: utf-8 -*-
# 檔案: tests/test_db_queries.py
# 說明: 對 src/phoenix_core/db_queries.py 中的函式進行單元測試。

import pytest
from src.phoenix_core.db_queries import query_logs_by_level

def test_query_success_logs(mock_db):
    """
    測試查詢 SUCCESS 等級的日誌。
    根據 conftest.py 中的設定，應返回 3 筆 SUCCESS 日誌。
    """
    results = query_logs_by_level(mock_db, 'SUCCESS', limit=10)
    assert len(results) == 3
    for row in results:
        assert row[2] == 'SUCCESS' # level 在第 3 個位置 (index 2)

def test_query_error_logs(mock_db):
    """
    測試查詢 ERROR 等級的日誌。
    根據 conftest.py 中的設定，應返回 2 筆 ERROR 日誌。
    """
    results = query_logs_by_level(mock_db, 'ERROR', limit=10)
    assert len(results) == 2
    for row in results:
        assert row[2] == 'ERROR'

def test_query_non_existent_level(mock_db):
    """
    測試查詢一個不存在的日誌等級。
    應返回一個空列表。
    """
    results = query_logs_by_level(mock_db, 'CRITICAL', limit=10)
    assert len(results) == 0
    assert results == []

def test_query_with_limit(mock_db):
    """
    測試 LIMIT 參數是否生效。
    查詢 SUCCESS 日誌，但將 limit 設為 1，應只返回 1 筆結果。
    """
    results = query_logs_by_level(mock_db, 'SUCCESS', limit=1)
    assert len(results) == 1
    assert results[0][2] == 'SUCCESS'
