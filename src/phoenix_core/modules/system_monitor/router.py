# 檔案: src/phoenix_core/modules/system_monitor/router.py (更新版)
from fastapi import APIRouter
# 思路框架: 從核心引擎導入我們需要的服務和數據模型。
from ...kernel.hardware import get_system_usage, SystemUsage

router = APIRouter(
    prefix="/monitor",
    tags=["系統監控 (System Monitor)"],
)

# 思路框架: 將 API 的回應模型指定為我們在 kernel 中定義的 SystemUsage 模型。
#           這確保了 API 的輸出與核心服務的定義保持一致。
@router.get("/health", response_model=SystemUsage)
async def get_health_status():
    """
    提供系統即時的健康狀態與資源使用率。
    """
    # 調用核心服務來獲取真實數據。
    return get_system_usage()
