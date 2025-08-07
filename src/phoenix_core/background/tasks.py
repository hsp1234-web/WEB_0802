# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/background/tasks.py
# 說明: 存放應用程式需要在背景運行的常駐任務。

import asyncio
from datetime import datetime, timezone

# 導入我們共享的資料庫管理器實例
from ..database import db_manager
from ..watchdog import HEARTBEAT_KEY
from ..utils.logger import logger

async def periodic_heartbeat(interval_seconds: int = 5):
    """
    定期將當前時間戳寫入資料庫，作為系統存活的信號。
    這是看門狗監控的主要目標。
    """
    await logger.log("INFO", "心跳任務已啟動。", source="Heartbeat")
    while True:
        try:
            current_time_str = datetime.now(timezone.utc).isoformat()
            # 使用 asyncio.to_thread 在異步事件循環中安全地調用阻塞的資料庫方法
            await asyncio.to_thread(db_manager.write_status_update, HEARTBEAT_KEY, current_time_str)
            # V68 修復：將日誌級別從 DEBUG 提升到 INFO，以確保看門狗可以監控到。
            await logger.log("INFO", f"HEARTBEAT PING: {current_time_str}", source="Heartbeat")
        except Exception as e:
            # 注意：我們的自訂 logger.log 沒有 exc_info 參數，但我們可以將 traceback 包含在訊息中
            import traceback
            error_message = f"心跳任務發生錯誤: {e}\n{traceback.format_exc()}"
            await logger.log("ERROR", error_message, source="Heartbeat")

        await asyncio.sleep(interval_seconds)
