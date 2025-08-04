# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/background/tasks.py
# 說明: 存放應用程式需要在背景運行的常駐任務。

import asyncio
from datetime import datetime, timezone

# 導入我們共享的資料庫管理器實例
from ..database import db_manager
from ..watchdog import HEARTBEAT_KEY

async def periodic_heartbeat(interval_seconds: int = 5):
    """
    一個週期性執行的背景任務，用於向資料庫寫入心跳信號。
    這能讓外部監控系統知道我們的服務仍然存活。
    """
    print(f"❤️  心跳背景任務已啟動，每 {interval_seconds} 秒更新一次。")
    while True:
        try:
            # 使用 value 欄位存放當前時間戳，方便直接查看
            current_time_str = datetime.now(timezone.utc).isoformat()
            db_manager.write_status_update(HEARTBEAT_KEY, current_time_str)
            # 在日誌中打印，以便於偵錯時觀察
            # print(f"❤️  心跳已更新: {current_time_str}")
        except Exception as e:
            # 在背景任務中，捕獲並打印錯誤至關重要，否則任務可能會無聲地失敗
            print(f"❌ 心跳任務發生錯誤: {e}")

        # 等待指定的間隔時間
        await asyncio.sleep(interval_seconds)
