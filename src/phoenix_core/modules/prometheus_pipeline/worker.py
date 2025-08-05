# -*- coding: utf-8 -*-
import asyncio
from phoenix_core.utils.logger import logger
from phoenix_core.modules.prometheus_pipeline.core.db.db_manager import DBManager
# 假設我們有一個管線執行的主函式
# from .pipelines.main_executor import run_pipeline_by_name

async def prometheus_worker_main_loop():
    """
    普羅米修斯管線工人的主循環。

    這個循環會定期檢查是否有新的管線任務需要執行。
    （這是一個簡化版本，真實世界中可能會使用更複雜的佇列系統）
    """
    logger.info("普羅米修斯工人 (Prometheus Worker) 啟動...")

    # 這裡只是一個範例，展示如何初始化 DBManager 並使用它
    # 在真實的實現中，管線的執行會更複雜
    try:
        db_manager = DBManager()
        logger.info(f"工人成功初始化 DBManager，使用資料庫路徑: {db_manager.db_path}")
    except Exception as e:
        logger.error(f"工人初始化 DBManager 失敗: {e}", exc_info=True)
        return # 初始化失敗，工人無法繼續

    while True:
        try:
            logger.info("普羅米修斯工人正在待命...")

            # TODO: 實現從佇列中獲取任務的邏輯
            # task = await get_next_task_from_queue()
            # if task:
            #     logger.info(f"收到新任務: {task.name}，開始執行...")
            #     await run_pipeline_by_name(task.name)
            #     logger.info(f"任務 {task.name} 執行完畢。")

            await asyncio.sleep(15) # 每 15 秒檢查一次
        except asyncio.CancelledError:
            logger.info("普羅米修斯工人收到關閉信號，正在優雅地關閉...")
            break
        except Exception as e:
            logger.error(f"普羅米修斯工人在執行循環中遇到未預期的錯誤: {e}", exc_info=True)
            # 發生錯誤後，等待一段時間再繼續，避免快速連續失敗
            await asyncio.sleep(60)

    logger.info("普羅米修斯工人已關閉。")

# 這是用來從 API router 添加任務到佇列的函式 (示意)
# async def add_pipeline_task(pipeline_name: str):
#     # TODO: 實現將任務寫入佇列的邏輯
#     logger.info(f"任務 '{pipeline_name}' 已被添加到執行佇列。")
#     pass
