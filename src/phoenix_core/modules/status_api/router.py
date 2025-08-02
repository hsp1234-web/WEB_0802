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


# --- API 路由器 ---

router = APIRouter(
    prefix="/api/v1/status",
    tags=["Status"],
)

# 模擬的後端資料
mock_db = {
    "status": {
        "current_stage": "服務運行中",
        "cpu_usage": 15.5,
        "ram_usage": 60.1,
        "apps_status": '{"dataprovider": "running", "system_monitor": "running"}'
    },
    "logs": [
        {"timestamp": "2025-08-02T10:30:00Z", "level": "INFO", "message": "API 服務已啟動"},
        {"timestamp": "2025-08-02T10:30:05Z", "level": "SUCCESS", "message": "資料提供者模組正常運行"},
        {"timestamp": "2025-08-02T10:30:10Z", "level": "ERROR", "message": "無法連接到外部數據源"},
        {"timestamp": "2025-08-02T10:30:15Z", "level": "BATTLE", "message": "策略 'Alpha-01' 已執行"},
        {"timestamp": "2025-08-02T10:30:20Z", "level": "CMD", "message": "執行指令: backtest --run"}
    ],
    "action_url": "http://localhost:8088/docs"
}


@router.get("/performance", response_model=PerformanceStatusResponse)
async def get_performance_status():
    """
    提供高頻率的系統效能指標 (CPU, RAM)。
    """
    return {
        "cpu_usage": mock_db["status"]["cpu_usage"],
        "ram_usage": mock_db["status"]["ram_usage"],
    }

@router.get("/dashboard", response_model=DashboardStatusResponse)
async def get_dashboard_status():
    """
    提供儀表板所需的主要狀態資訊 (服務狀態, 日誌等)。
    """
    import os
    import json

    # --- 日誌過濾邏輯 ---
    config_path = os.getenv("PHOENIX_CONFIG_PATH")
    enabled_log_levels = {}
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                # 使用 .get() 提供預設值，以確保健壯性
                enabled_log_levels = config_data.get("log_settings", {}).get("levels", {})
        except (json.JSONDecodeError, FileNotFoundError):
            # 如果設定檔有問題或找不到，則預設為空，即顯示所有日誌
            enabled_log_levels = {}

    all_logs = mock_db["logs"]

    # 如果 `enabled_log_levels` 為空 (例如，設定檔中沒有相關區塊)，則預設顯示所有日誌
    if not enabled_log_levels:
        filtered_logs = all_logs
    else:
        # 只選擇在設定中明確設定為 True 的等級
        filtered_logs = [
            log for log in all_logs
            if enabled_log_levels.get(log["level"], False)
        ]
    # --- 過濾邏輯結束 ---

    return {
        "current_stage": mock_db["status"]["current_stage"],
        "apps_status": json.loads(mock_db["status"]["apps_status"]),
        "logs": filtered_logs, # 返回過濾後的日誌
        "action_url": mock_db["action_url"]
    }
