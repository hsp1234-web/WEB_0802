# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/background/worker.py
# 說明: 背景任務管理器。負責啟動、停止和管理應用程式中的所有背景任務。

import asyncio
import logging
from .tasks import periodic_heartbeat
from ..modules.transcription.worker import transcription_worker_main_loop
from ..modules.prometheus_pipeline.worker import prometheus_worker_main_loop

logger = logging.getLogger(__name__)

def start_background_tasks():
    """
    啟動所有應用程式需要的背景任務。
    """
    logger.info("正在啟動背景任務管理器...")

    # 使用 asyncio.create_task 來安排協程在事件循環中運行
    # 這是一個非阻塞操作
    # --- 恢復所有任務 ---
    asyncio.create_task(periodic_heartbeat())
    asyncio.create_task(transcription_worker_main_loop())
    asyncio.create_task(prometheus_worker_main_loop())

    logger.info("所有背景任務已成功提交至事件循環。")

# 在未來，這裡可以添加停止或管理任務的函式
# def stop_background_tasks():
#     ...
