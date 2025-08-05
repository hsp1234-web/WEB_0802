# 檔案: src/phoenix_core/kernel/hardware.py
import psutil
from pydantic import BaseModel
from typing import Dict, Any

# 延遲導入，避免在沒有 GPU 的環境中強制依賴 torch
torch = None

def _lazy_import_torch():
    global torch
    if torch is None:
        try:
            import torch as torch_
            torch = torch_
        except ImportError:
            # 在沒有 torch 的環境中，這是一個正常的 fallback
            pass

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

def get_best_hardware_config() -> Dict[str, Any]:
    """
    偵測系統硬體，並返回最適合 faster-whisper 的設定。
    """
    _lazy_import_torch()

    if torch and torch.cuda.is_available():
        # TODO: 可以在這裡增加更詳細的 GPU 型號判斷，以選擇最佳 compute_type
        return {"device": "cuda", "compute_type": "float16"}
    else:
        return {"device": "cpu", "compute_type": "int8"}
