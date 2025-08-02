
from fastapi import FastAPI
app = FastAPI(title="Phoenix Core API")

@app.get("/api/v1/status", tags=["Status"])
async def get_status():
    """回傳當前的系統狀態。 (模擬)"""
    return {
        "status": {
            "current_stage": "服務運行中",
            "cpu_usage": 12.5,
            "ram_usage": 55.8,
            "apps_status": '{"dataprovider": "running", "system_monitor": "running"}'
        },
        "logs": [
            {"timestamp": "2025-08-02T10:30:00Z", "level": "INFO", "message": "API 服務已啟動"},
            {"timestamp": "2025-08-02T10:30:05Z", "level": "SUCCESS", "message": "資料提供者模組正常運行"}
        ],
        "action_url": "http://localhost:8088/docs" # 提供 swagger UI
    }
