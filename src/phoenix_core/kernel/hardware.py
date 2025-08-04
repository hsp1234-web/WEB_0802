# 檔案: src/phoenix_core/kernel/hardware.py
import psutil
from pydantic import BaseModel

class SystemUsage(BaseModel):
    """
    定義系統使用率的數據模型，確保數據格式的一致性。
    """
    cpu_percent: float
    memory_percent: float

def get_system_usage() -> SystemUsage:
    """
    從系統獲取即時的 CPU 和記憶體使用率。
    這是一個可供任何模組調用的共享核心服務。
    """
    cpu_percent = psutil.cpu_percent(interval=None) # interval=None 為非阻塞式獲取
    memory_info = psutil.virtual_memory()

    return SystemUsage(
        cpu_percent=cpu_percent,
        memory_percent=memory_info.percent
    )
