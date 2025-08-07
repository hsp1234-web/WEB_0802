# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/background/tasks.py
# 說明: 存放應用程式需要在背景運行的常駐任務。

import asyncio
from datetime import datetime, timezone
from pathlib import Path

# 導入我們共享的資料庫管理器實例
from ..database import db_manager
from ..watchdog import HEARTBEAT_KEY
from ..utils.logger import logger

# 為基於檔案的看門狗定義心跳檔案的路徑
# 專案根目錄是此檔案往上追溯 3 層
HEARTBEAT_FILE = Path(__file__).resolve().parents[3] / "storage" / "heartbeat.timestamp"


async def periodic_heartbeat(interval_seconds: int = 5):
    """
    定期將當前時間戳寫入資料庫並更新一個檔案的時間戳，作為系統存活的雙重信號。
    """
    await logger.log("INFO", "心跳任務已啟動。", source="Heartbeat")

    # 確保 storage 目錄存在
    await asyncio.to_thread(HEARTBEAT_FILE.parent.mkdir, exist_ok=True)

    while True:
        try:
            current_time_str = datetime.now(timezone.utc).isoformat()
            # 異步地執行資料庫寫入和檔案觸控操作
            await asyncio.gather(
                asyncio.to_thread(db_manager.write_status_update, HEARTBEAT_KEY, current_time_str),
                asyncio.to_thread(HEARTBEAT_FILE.touch)
            )

            # V68 修復：將日誌級別從 DEBUG 提升到 INFO，以確保看門狗可以監控到。
            await logger.log("INFO", f"HEARTBEAT PING: {current_time_str}", source="Heartbeat")
        except Exception as e:
            # 注意：我們的自訂 logger.log 沒有 exc_info 參數，但我們可以將 traceback 包含在訊息中
            import traceback
            error_message = f"心跳任務發生錯誤: {e}\n{traceback.format_exc()}"
            await logger.log("ERROR", error_message, source="Heartbeat")

        await asyncio.sleep(interval_seconds)
