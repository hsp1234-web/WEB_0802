# 檔案: src/phoenix_core/modules/status_api/router.py
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


# --- 導入項目核心模組 ---
import psutil
import os
import json
from ...database import db_manager
from ...db_queries import query_logs_by_level
from ...watchdog import check_heartbeat_status
from ...kernel.settings import settings

# --- API 路由器 ---
router = APIRouter(
    prefix="/api/v1/status",
    tags=["Status"],
)

@router.get("/performance", response_model=PerformanceStatusResponse)
async def get_performance_status():
    """
    提供高頻率的系統效能指標 (CPU, RAM)。
    """
    return {
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage": psutil.virtual_memory().percent,
    }

@router.get("/dashboard", response_model=DashboardStatusResponse)
async def get_dashboard_status():
    """
    提供儀表板所需的主要狀態資訊 (服務狀態, 日誌等)，從真實資料庫讀取。
    """
    conn = db_manager.get_connection()

    # --- 日誌過濾邏輯 (每次請求時重新讀取設定) ---
    config_path = os.getenv("PHOENIX_CONFIG_PATH")
    enabled_log_levels = {}
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                enabled_log_levels = config_data.get("log_settings", {}).get("levels", {})
        except (json.JSONDecodeError, FileNotFoundError):
            enabled_log_levels = {} # 發生錯誤時，顯示所有日誌

    # 1. 獲取日誌
    all_logs = []
    # 如果 enabled_log_levels 為空 (未設定或設定檔有誤)，則獲取所有等級的日誌
    levels_to_fetch = [level for level, is_enabled in enabled_log_levels.items() if is_enabled] if enabled_log_levels else ["INFO", "SUCCESS", "ERROR", "BATTLE", "CMD", "CRITICAL", "LOG_SHELL"]

    for level in levels_to_fetch:
        logs_for_level = query_logs_by_level(conn, level, limit=50)
        all_logs.extend(logs_for_level)

    # 根據時間戳排序所有收集到的日誌
    all_logs.sort(key=lambda x: x[1], reverse=True)
    display_logs = all_logs[:50] # 取最新的 N 筆

    formatted_logs = [
        LogEntry(timestamp=row[1], level=row[2], message=row[4])
        for row in display_logs
    ]

    # 2. 獲取當前階段與心跳狀態
    heartbeat = check_heartbeat_status(conn, threshold_seconds=15)
    current_stage = "服務運行中"
    if heartbeat != 'OK':
        current_stage = f"服務異常 ({heartbeat})"


    # 3. 獲取 App 狀態 (此處暫時保留模擬，因其邏輯尚未完全建立)
    apps_status = {"dataprovider": "running", "system_monitor": "running"}

    # 4. 獲取行動 URL (暫時保留模擬)
    action_url = "http://localhost:8088/docs"

    return {
        "current_stage": current_stage,
        "apps_status": apps_status,
        "logs": formatted_logs,
        "action_url": action_url
    }
