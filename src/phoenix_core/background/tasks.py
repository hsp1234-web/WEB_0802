# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/background/tasks.py
# 說明: 存放應用程式需要在背景運行的常駐任務。

import asyncio
import logging
from datetime import datetime, timezone

# 導入我們共享的資料庫管理器實例
from ..database import db_manager
from ..watchdog import HEARTBEAT_KEY

# 獲取一個 logger 實例，這是進行日誌記錄的最佳實踐
logger = logging.getLogger(__name__)

async def periodic_heartbeat(interval_seconds: int = 5):
    """
    一個極簡化的心跳任務，用於最終的偵錯。
    它只打印到 stdout，沒有任何外部依賴。
    """
    print("--- HEARTBEAT TASK CREATED ---", flush=True)
    await asyncio.sleep(1)
    print("--- HEARTBEAT TASK STARTED ---", flush=True)
    while True:
        print(f"--- HEARTBEAT PING ({datetime.now(timezone.utc)}) ---", flush=True)
        await asyncio.sleep(interval_seconds)
