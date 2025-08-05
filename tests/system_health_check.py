# 檔案: tests/system_health_check.py
# 說明: 用於對 asyncio 和背景任務進行底層健康檢查的獨立測試。

import asyncio
import pytest
from typing import List

# 使用 pytest-asyncio 的 'asyncio' mode
pytestmark = pytest.mark.asyncio

async def simple_background_task(tracking_list: List[int]):
    """一個簡單的背景任務，在短暫延遲後修改一個共享列表。"""
    await asyncio.sleep(0.1)
    tracking_list.append(1)

@pytest.mark.asyncio
async def test_pure_asyncio_background_task():
    """
    測試一：純粹的 asyncio 測試。
    目的：驗證 asyncio.create_task 是否能在 pytest-asyncio 的事件循環中正常調度背景任務。
    這不依賴任何專案程式碼。
    """
    # 1. 準備一個共享狀態的物件
    result_tracker = []

    # 2. 創建並啟動背景任務
    print("\n[Test 1] 正在創建純 asyncio 背景任務...")
    asyncio.create_task(simple_background_task(result_tracker))

    # 3. 等待足夠長的時間讓背景任務完成
    #    這個等待是關鍵，它讓出控制權給事件循環，使其有機會執行背景任務
    print("[Test 1] 等待背景任務執行...")
    await asyncio.sleep(0.2)

    # 4. 驗證背景任務是否已執行
    print("[Test 1] 驗證結果...")
    assert len(result_tracker) == 1
    assert result_tracker[0] == 1
    print("[Test 1] 純 asyncio 背景任務測試成功！")


# 從專案中導入我們想要測試的背景任務
from src.phoenix_core.background.tasks import periodic_heartbeat

@pytest.mark.asyncio
async def test_project_heartbeat_task_direct_execution(capsys):
    """
    測試二：專案心跳任務測試。
    目的：驗證我們專案的 `periodic_heartbeat` 函式在被 `pytest-asyncio` 直接調用時能否運行。
    這將問題範圍縮小到 Uvicorn vs. Pytest 的環境差異。
    """
    # 1. 創建並啟動心跳任務，使用較短的間隔以快速得到結果
    print("\n[Test 2] 正在創建專案心跳背景任務...")
    heartbeat_task = asyncio.create_task(periodic_heartbeat(interval_seconds=0.1))

    # 2. 等待一小段時間，讓任務至少有機會執行一到兩次
    print("[Test 2] 等待心跳任務執行...")
    await asyncio.sleep(0.25)

    # 3. 停止背景任務，防止它無限運行下去
    print("[Test 2] 正在停止任務...")
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        print("[Test 2] 任務已成功取消。")

    # 4. 捕獲並驗證 stdout 的輸出
    captured = capsys.readouterr()
    print("[Test 2] 驗證輸出...")
    assert "HEARTBEAT TASK CREATED" in captured.out
    assert "HEARTBEAT TASK STARTED" in captured.out
    assert "HEARTBEAT PING" in captured.out
    print("[Test 2] 專案心跳任務測試成功！")
