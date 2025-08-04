# -*- coding: utf-8 -*-
# 檔案: tests/integration/test_log_filtering.py
# 說明: 驗證後端 API 是否能根據 config.json 正確過濾日誌。

import subprocess
import sys
import os
import time
import json
import httpx
from pathlib import Path
import pytest
import socket
import shutil

from pathlib import Path

def create_config(path: Path, log_levels: dict):
    """建立一個測試用的 config.json 檔案"""
    config = {
        "log_settings": {
            "levels": log_levels
        }
    }
    with open(path, "w") as f:
        json.dump(config, f)

@pytest.mark.parametrize("enabled_levels, expected_levels", [
    (
        {"INFO": True, "SUCCESS": False, "ERROR": True, "BATTLE": False, "CMD": False},
        {"INFO", "ERROR"}
    ),
    (
        {"INFO": True, "SUCCESS": True, "ERROR": True, "BATTLE": True, "CMD": True},
        {"INFO", "SUCCESS", "ERROR", "BATTLE", "CMD"}
    ),
    (
        {"INFO": False, "SUCCESS": False, "ERROR": False, "BATTLE": False, "CMD": False},
        set()
    ),
    (
        {"BATTLE": True}, # 只啟用一個
        {"BATTLE"}
    )
])
def test_log_filtering(live_server, enabled_levels, expected_levels):
    """
    測試 API 是否根據 config.json 中的設定正確過濾日誌。
    """
    port = live_server["port"]
    config_path = live_server["config_path"]

    # 1. 根據測試參數建立設定檔
    create_config(config_path, enabled_levels)

    # 2. 呼叫 API 端點
    # 需要給伺服器一點時間來重新載入檔案，雖然 uvicorn 不會自動重載 json，
    # 但我們的 API 每次請求都會讀取檔案，所以直接請求即可。
    time.sleep(0.1)
    api_url = f"http://127.0.0.1:{port}/api/v1/status/dashboard"
    try:
        response = httpx.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except (httpx.RequestError, json.JSONDecodeError) as e:
        pytest.fail(f"API 請求失敗: {e}")

    # 3. 驗證回傳的日誌
    assert "logs" in data, "API 回應中缺少 'logs' 欄位"

    returned_levels = {log["level"] for log in data["logs"]}

    assert returned_levels == expected_levels, \
        f"日誌過濾不正確！預期看到 {expected_levels}，但實際看到 {returned_levels}"
