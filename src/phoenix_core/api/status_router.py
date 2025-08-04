# 檔案: src/phoenix_core/api/status_router.py
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json
import psutil

# 導入應用程式的核心組件
from ..kernel.settings import settings
from ..database import db_manager
from ..db_queries import query_logs_by_levels

# --- Pydantic 回應模型 ---

class LogEntry(BaseModel):
    """定義日誌記錄的結構，與資料庫查詢結果對應"""
    id: int
    timestamp: str
    level: str
    source: str | None
    message: str

class PerformanceStatusResponse(BaseModel):
    cpu_usage: float = Field(..., example=12.5)
    ram_usage: float = Field(..., example=55.8)

class DashboardStatusResponse(BaseModel):
    current_stage: str = Field(..., example="服務運行中")
    apps_status: Dict[str, Any] = Field(..., example={"dataprovider": "running"})
    logs: List[LogEntry]
    action_url: str = Field(..., example="/docs")


# --- API 路由器 ---

router = APIRouter()

@router.get("/performance", response_model=PerformanceStatusResponse, tags=["Status"])
async def get_performance_status():
    """
    提供高頻率的系統效能指標 (CPU, RAM)。
    """
    return {
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage": psutil.virtual_memory().percent,
    }

@router.get("/dashboard", response_model=DashboardStatusResponse, tags=["Status"])
async def get_dashboard_status():
    """
    提供儀表板所需的主要狀態資訊 (服務狀態, 日誌等)，
    這些資訊現在直接從資料庫和設定檔中讀取。
    """
    # 1. 決定要顯示哪些等級的日誌
    enabled_levels = [
        level for level, is_enabled in settings.LOG_SETTINGS.model_dump().items() if is_enabled
    ]

    # 2. 從資料庫查詢日誌
    # db_manager 會處理執行緒安全的連線
    conn = db_manager.get_connection()
    try:
        log_records = query_logs_by_levels(conn, enabled_levels, limit=50)

        # 將資料庫記錄 (元組) 轉換為 LogEntry 物件列表
        logs = [
            LogEntry(id=row[0], timestamp=row[1], level=row[2], source=row[3], message=row[4])
            for row in log_records
        ]

        # 3. 從資料庫獲取其他狀態資訊
        current_stage = db_manager.get_status("current_stage") or "初始化..."
        apps_status_json = db_manager.get_status("apps_status") or "{}"

        try:
            apps_status = json.loads(apps_status_json)
        except json.JSONDecodeError:
            apps_status = {"error": "無法解析應用程式狀態"}

    finally:
        # 確保資料庫連線總是會被關閉
        # 雖然 db_manager 是執行緒本地的，但好的實踐是顯式地關閉
        # 在這個應用中，因為是單例，所以可能不會立即關閉，但邏輯上是正確的
        db_manager.close_connection()

    # 4. 組合回應
    return DashboardStatusResponse(
        current_stage=current_stage,
        apps_status=apps_status,
        logs=logs,
        action_url="/docs"
    )
