# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/background/tasks.py
# 說明: 存放應用程式需要在背景運行的常駐任務。

import asyncio
import logging
from datetime import datetime, timezone

# 導入我們共享的資料庫管理器實例
from ..database import db_manager
from ..watchdog import HEARTBEAT_KEY
from ..modules.transcription.worker import transcription_worker_main_loop
from ..modules.prometheus_pipeline.worker import prometheus_worker_main_loop

# 獲取一個 logger 實例，這是進行日誌記錄的最佳實踐
logger = logging.getLogger(__name__)

async def periodic_heartbeat(interval_seconds: int = 5):
    """
    一個週期性執行的背景任務，用於向資料庫寫入心跳信號。
    這能讓外部監控系統知道我們的服務仍然存活。
    """
    logger.info(f"❤️  心跳背景任務已啟動，每 {interval_seconds} 秒更新一次。")
    while True:
        try:
            # 使用 value 欄位存放當前時間戳，方便直接查看
            current_time_str = datetime.now(timezone.utc).isoformat()
            db_manager.write_status_update(HEARTBEAT_KEY, current_time_str)
            logger.debug(f"❤️  心跳已更新: {current_time_str}")
        except Exception:
            # 使用 logger.exception 會自動包含堆疊追蹤訊息，非常適合除錯
            logger.exception("❌ 心跳任務發生嚴重錯誤")

        # 等待指定的間隔時間
        await asyncio.sleep(interval_seconds)
