# 檔案: src/phoenix_core/api/status_router.py
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- Pydantic 回應模型 ---

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str

class PerformanceStatusResponse(BaseModel):
    cpu_usage: float = Field(..., example=12.5)
    ram_usage: float = Field(..., example=55.8)

class DashboardStatusResponse(BaseModel):
    current_stage: str = Field(..., example="服務運行中")
    apps_status: Dict[str, Any] = Field(..., example={"dataprovider": "running"})
    logs: List[LogEntry]
    action_url: str = Field(..., example="http://localhost:8088/docs")


# --- API 路由器 ---

router = APIRouter()

# 模擬的後端資料 (最終會被真實的系統狀態取代)
mock_db = {
    "status": {
        "current_stage": "服務運行中",
        "cpu_usage": 15.5,
        "ram_usage": 60.1,
        "apps_status": '{"dataprovider": "running", "system_monitor": "running"}'
    },
    "logs": [
        {"timestamp": "2025-08-02T10:30:00Z", "level": "INFO", "message": "API 服務已啟動"},
        {"timestamp": "2025-08-02T10:30:05Z", "level": "SUCCESS", "message": "資料提供者模組正常運行"}
    ],
    "action_url": "http://localhost:8088/docs"
}


@router.get("/performance", response_model=PerformanceStatusResponse, tags=["Status"])
async def get_performance_status():
    """
    提供高頻率的系統效能指標 (CPU, RAM)。
    """
    # 注意：這裡的資料最終會來自一個即時的硬體監控服務。
    return {
        "cpu_usage": mock_db["status"]["cpu_usage"],
        "ram_usage": mock_db["status"]["ram_usage"],
    }

@router.get("/dashboard", response_model=DashboardStatusResponse, tags=["Status"])
async def get_dashboard_status():
    """
    提供儀表板所需的主要狀態資訊 (服務狀態, 日誌等)。
    """
    # 注意：這裡的資料最終會來自後端的核心狀態管理器。
    import json
    return {
        "current_stage": mock_db["status"]["current_stage"],
        "apps_status": json.loads(mock_db["status"]["apps_status"]),
        "logs": mock_db["logs"],
        "action_url": mock_db["action_url"]
    }
