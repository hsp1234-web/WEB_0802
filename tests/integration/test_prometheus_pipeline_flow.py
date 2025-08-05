# -*- coding: utf-8 -*-
import pytest
import asyncio
import threading
import uvicorn
import httpx
import os
from pathlib import Path
import time

from phoenix_core.main import app as real_app
from phoenix_core.modules.prometheus_pipeline.worker import prometheus_worker_main_loop
from phoenix_core.kernel.settings import settings

# 設定測試環境的資料庫路徑，避免污染開發環境
TEST_STORAGE_DIR = Path(__file__).parent / "test_runtime_storage"

# Pytest 的非同步測試設定
@pytest.mark.asyncio
class TestPrometheusPipelineFlow:
    """
    對普羅米修斯管線的完整端對端流程進行整合測試。
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup_test_environment(self, mocker):
        """
        在所有測試運行前，使用 mocker 來修補設定，將資料庫路徑指向臨時目錄。
        """
        # 清理舊的測試檔案
        if TEST_STORAGE_DIR.exists():
            for item in TEST_STORAGE_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                else:
                    item.rmdir()
            TEST_STORAGE_DIR.rmdir()
        TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        # 使用 mocker 來修補 settings 物件
        # 注意：屬性名稱必須與 resource_settings.yml 中定義的完全匹配（小寫）
        mocker.patch.object(settings.prometheus_pipeline.database, 'main_db_path', str(TEST_STORAGE_DIR / "factors.duckdb"))
        mocker.patch.object(settings.prometheus_pipeline.database, 'data_warehouse_path', str(TEST_STORAGE_DIR / "data_warehouse.duckdb"))
        mocker.patch.object(settings.prometheus_pipeline.database, 'task_queue_db_path', str(TEST_STORAGE_DIR / "task_queue.db"))

        yield

        # 測試結束後清理
        # setup_test_environment fixture 已經處理了清理，此處無需重複


    @pytest.fixture(scope="class")
    def live_api_server(self):
        """
        一個 fixture，它會在背景執行緒中啟動一個真實的 uvicorn 伺服器。
        這使得我們的測試可以直接對 API 發送網路請求。
        """
        config = uvicorn.Config(real_app, host="127.0.0.1", port=8008, log_level="info")
        server = uvicorn.Server(config)

        server_thread = threading.Thread(target=server.run)
        server_thread.start()

        # 等待伺服器啟動
        time.sleep(2)

        yield "http://127.0.0.1:8008"

        # 測試結束後，優雅地關閉伺服器
        server.should_exit = True
        server_thread.join()

    @pytest.fixture(scope="class")
    async def live_prometheus_worker(self):
        """
        一個 fixture，它會在背景啟動普羅米修斯管線的工人。
        """
        worker_task = asyncio.create_task(prometheus_worker_main_loop())

        # 給工人一點時間來完成初始化
        await asyncio.sleep(1)

        yield

        # 測試結束後，取消工人任務
        worker_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker_task

    async def test_run_pipeline_e2e(self, live_api_server, live_prometheus_worker):
        """
        測試一個完整的端對端流程：
        1. 呼叫 API 觸發管線。
        2. 由於工人也在運行，它應該會執行（簡化的）任務。
        3. 驗證管線執行後是否產生了預期的檔案。
        """
        api_url = f"{live_api_server}/prometheus/run-pipeline"

        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json={"pipeline_name": "build-feature-store"}, timeout=10)
            assert response.status_code == 202
            assert "Pipeline run accepted" in response.json()["message"]

        # 給工人一些時間來執行它的（簡化版）任務
        # 在這個測試中，工人啟動後會初始化 DBManager，這會創建資料庫檔案
        await asyncio.sleep(2)

        # 從 (已修補的) settings 物件獲取路徑來進行驗證
        main_db_path = Path(settings.prometheus_pipeline.database.main_db_path)
        dw_path = Path(settings.prometheus_pipeline.database.data_warehouse_path)

        assert main_db_path.exists(), f"主資料庫檔案 {main_db_path} 未被創建！"
        assert dw_path.exists(), f"數據倉庫檔案 {dw_path} 未被創建！"

        # 可以在這裡添加更多驗證，例如連接到資料庫並檢查資料表
