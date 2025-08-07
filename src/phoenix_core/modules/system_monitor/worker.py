# src/phoenix_core/modules/system_monitor/worker.py
import asyncio
import traceback

from ...kernel.settings import settings
from ...utils.logger import logger
from ...utils.resource_monitor import log_system_resources

async def system_monitor_worker_main_loop():
    """
    系統監控工人的主循環，定期記錄系統資源使用情況。
    """
    await logger.log("INFO", "系統監控工人背景任務已啟動，開始記錄資源使用情況...", source="SystemMonitorWorker")

    poll_interval = settings.get("SYSTEM_MONITOR_POLL_INTERVAL", 60) # 預設60秒

    while True:
        try:
            await logger.log("DEBUG", "正在記錄系統資源...", source="SystemMonitorWorker")
            # resource_monitor.py 中的 log_system_resources 已經處理了所有邏輯
            await asyncio.to_thread(log_system_resources)
            await logger.log("DEBUG", "系統資源記錄完畢。", source="SystemMonitorWorker")

            await asyncio.sleep(poll_interval)
        except Exception as e:
            error_message = traceback.format_exc()
            await logger.log("CRITICAL", f"系統監控工人在主循環中發生無法恢復的嚴重錯誤: {e}\n{error_message}", source="SystemMonitorWorker")
            # 在發生嚴重錯誤時，等待更長的時間再重試
            await asyncio.sleep(poll_interval * 5)

if __name__ == "__main__":
    # 允許獨立執行此工人進行測試
    asyncio.run(system_monitor_worker_main_loop())
