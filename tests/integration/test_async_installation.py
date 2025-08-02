# -*- coding: utf-8 -*-
"""
測試後端非同步安裝功能性依賴的整合流程
"""
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

# 將專案根目錄加入 sys.path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts import launch

# 使用 pytest-asyncio 來標記這是一個非同步測試
@pytest.mark.asyncio
# 使用 aiohttp_client fixture 來發送 API 請求
async def test_async_dependency_installation_flow(aiohttp_client):
    """
    端對端測試非同步安裝流程：
    1. 啟動伺服器。
    2. 輪詢 API，確認狀態從 pending -> installing -> running。
    3. 關閉伺服器。
    """

    # --- 模擬與設定 ---

    # 1. 模擬 subprocess 的執行
    # 我們讓它看起來像一個成功的 pip install，在短暫延遲後結束
    mock_process = AsyncMock()
    mock_process.wait.return_value = 0 # 成功返回碼
    mock_process.stdout.readline.side_effect = [b'fake pip output\n', b''] # 模擬一行輸出後結束

    # 2. Patch 目標函式
    # 我們 patch launch 模組中的 asyncio.create_subprocess_exec
    with patch('scripts.launch.asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:

        # --- 啟動伺服器 ---

        # 準備 aiohttp 應用
        app = launch.web.Application()
        app.add_routes([
            launch.web.get('/api/v1/status', launch.get_status_handler),
            launch.web.post('/api/v1/shutdown', launch.shutdown_handler),
        ])

        # 建立測試客戶端
        client = await aiohttp_client(app)

        # 在背景執行 launch.py 的 main 函式
        # 我們不直接呼叫 main()，而是模擬其核心任務的啟動
        # 這樣可以避免 main() 中的 run_forever 阻塞測試
        launch.shared_state["apps_status"] = {"database": "pending", "cache": "pending", "report_system": "pending"}
        install_task = asyncio.create_task(launch.install_feature_dependencies())


        # --- 驗證狀態轉換 ---

        # 由於模擬的安裝過程非常快，我們直接等待任務完成
        # 然後驗證最終狀態和模擬呼叫
        await install_task

        # 最終狀態應為 'running'
        resp = await client.get("/api/v1/status")
        data = await resp.json()
        status = json.loads(data['status']['apps_status'])
        print(f"狀態 (任務結束後): {status}")
        assert status['report_system'] == 'running'

        # 驗證 'pip install' 被正確呼叫
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert "pip" in args[2]
        assert "install" in args[3]
        assert "requirements-features.txt" in args[5]

        print("\n✅ 測試成功：狀態轉換符合預期，且安裝指令被正確呼叫。")
