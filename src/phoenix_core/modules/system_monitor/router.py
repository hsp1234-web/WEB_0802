# 檔案: src/phoenix_core/modules/system_monitor/router.py
from fastapi import APIRouter

# 思路框架: 每個模組的 API 都應該是一個獨立的 APIRouter 實例。
#           使用 prefix 和 tags 來組織 API，使其在文件中清晰可辨。
router = APIRouter(
    prefix="/monitor",
    tags=["系統監控 (System Monitor)"],
)

@router.get("/health")
async def get_health_status():
    """
    提供系統健康狀態的基礎資訊。
    """
    # 為了保持簡單，我們先返回靜態數據。
    return {"status": "healthy", "cpu_load": "10%", "memory": "25%"}
