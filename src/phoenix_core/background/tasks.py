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
    定期將當前時間戳寫入資料庫，作為系統存活的信號。
    這是看門狗監控的主要目標。
    """
    logger.info("心跳任務已啟動。")
    while True:
        try:
            current_time_str = datetime.now(timezone.utc).isoformat()
            # 使用 asyncio.to_thread 在異步事件循環中安全地調用阻塞的資料庫方法
            await asyncio.to_thread(db_manager.write_status_update, HEARTBEAT_KEY, current_time_str)
            logger.debug(f"HEARTBEAT PING: {current_time_str}")
        except Exception as e:
            logger.error(f"心跳任務發生錯誤: {e}", exc_info=True)

        await asyncio.sleep(interval_seconds)
