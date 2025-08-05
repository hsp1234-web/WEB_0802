# 檔案: src/phoenix_core/modules/system_monitor/router.py
from fastapi import APIRouter
# 從核心 kernel 導入我們需要的服務和資料模型。
from ...kernel.hardware import get_system_usage, SystemUsage

router = APIRouter(
    prefix="/monitor",
    tags=["系統監控 (System Monitor)"],
)

# 修正：將路由從 "/health" 改為 "/"
# 如此一來，這個端點的完整路徑就會是 APIRouter 的前綴 "/monitor"，
# 這能修正 E2E 測試中預期路徑與實際路徑不符 (404 Not Found) 的問題。
# 同時，將 API 的回應模型指定為我們在 kernel 中定義的 SystemUsage 模型，
# 以確保 API 的輸出與核心服務的定義保持一致。
@router.get("/", response_model=SystemUsage)
async def get_health_status():
    """
    提供系統即時的健康狀態與資源使用率。
    """
    # 調用核心服務來獲取真實數據。
    return get_system_usage()
