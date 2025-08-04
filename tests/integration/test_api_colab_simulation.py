# -*- coding: utf-8 -*-
# 檔案: tests/integration/test_api_colab_simulation.py
# 說明: 模擬 Colab Runner 的核心 API 互動，驗證後端功能。

import time
import json
import httpx
from pathlib import Path
import pytest

# 輔助函式，用於在測試期間動態建立設定檔
def create_config(path: Path, log_levels: dict):
    """建立一個測試用的 config.json 檔案"""
    config = {
        "log_settings": {
            "levels": log_levels
        }
    }
    with open(path, "w") as f:
        json.dump(config, f)

# --- 測試案例 ---

def test_api_reachability(live_server):
    """
    測試案例 1: 驗證伺服器是否成功啟動且根目錄可訪問。
    這是一個基本的「冒煙測試」。
    """
    base_url = live_server["base_url"]
    try:
        response = httpx.get(f"{base_url}/", timeout=10)
        response.raise_for_status()
        # 我們期望根目錄能返回 wolf.html
        assert "text/html" in response.headers["content-type"]
    except httpx.RequestError as e:
        pytest.fail(f"API 可及性測試失敗: 無法連接到 {base_url}。錯誤: {e}")
    except httpx.HTTPStatusError as e:
        pytest.fail(f"API 可及性測試失敗: {base_url} 返回錯誤狀態碼 {e.response.status_code}")

@pytest.mark.parametrize("enabled_levels, expected_levels", [
    (
        {"INFO": True, "SUCCESS": True, "ERROR": True, "BATTLE": True, "CMD": True, "CRITICAL": True, "LOG_SHELL": True},
        {"INFO", "SUCCESS", "ERROR", "BATTLE", "CMD", "CRITICAL", "LOG_SHELL"}
    ),
    (
        {"INFO": False, "SUCCESS": False, "ERROR": True, "BATTLE": True, "CMD": False, "CRITICAL": True, "LOG_SHELL": False},
        {"ERROR", "BATTLE", "CRITICAL"}
    ),
    (
        {"INFO": False, "SUCCESS": False, "ERROR": False, "BATTLE": False, "CMD": False, "CRITICAL": False, "LOG_SHELL": False},
        set()
    )
])
def test_log_filtering_logic(live_server, enabled_levels, expected_levels):
    """
    測試案例 2: 系統性地驗證後端日誌過濾功能。
    """
    api_url = f"{live_server['base_url']}/api/v1/status/dashboard"
    config_path = live_server["config_path"]

    # 1. 根據測試參數建立設定檔
    create_config(config_path, enabled_levels)
    time.sleep(0.2) # 給予系統一點時間反應（雖然我們的 API 會即時讀取）

    # 2. 呼叫 API
    try:
        response = httpx.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        pytest.fail(f"API 請求失敗: {e}")

    # 3. 驗證日誌
    returned_levels = {log["level"] for log in data.get("logs", [])}
    assert returned_levels == expected_levels, \
        f"日誌過濾不正確！預期看到 {expected_levels}，但實際看到 {returned_levels}"

def test_heartbeat_is_updating(live_server):
    """
    測試案例 3: 驗證後端服務是真的「活著」，而不是殭屍進程。
    """
    api_url = f"{live_server['base_url']}/api/v1/status/dashboard"

    try:
        # 第一次請求，確認服務初始狀態正常
        response1 = httpx.get(api_url, timeout=5)
        response1.raise_for_status()
        data1 = response1.json()
        assert data1["current_stage"] == "服務運行中", \
            f"預期初始狀態為 '服務運行中'，但得到 '{data1['current_stage']}'"

        # 等待足夠長的時間，讓心跳任務至少能執行一次 (心跳間隔為 5 秒)
        print("\n等待 6 秒以檢測心跳更新...")
        time.sleep(6)

        # 第二次請求
        response2 = httpx.get(api_url, timeout=5)
        response2.raise_for_status()
        data2 = response2.json()
        assert data2["current_stage"] == "服務運行中", \
            f"等待後，預期狀態仍為 '服務運行中'，但得到 '{data2['current_stage']}'"

        # 這裡我們不直接比較時間戳，而是依賴 check_heartbeat_status 的邏輯。
        # 只要兩次檢查都是 "服務運行中"，就代表心跳在 15 秒的閾值內被更新了。
        # 為了讓測試更明確，我們可以比較日誌的數量或內容是否有變化。
        assert len(data2.get("logs", [])) >= len(data1.get("logs", [])), "第二次請求的日誌數量不應少於第一次"
        print("✅ 心跳測試成功：服務在等待後依然回報為運行中狀態。")

    except Exception as e:
        pytest.fail(f"心跳測試執行時發生錯誤: {e}")
