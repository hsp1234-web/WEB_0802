# -*- coding: utf-8 -*-
# 繁體中文註解: 將 UI 事件日誌記錄功能放在這裡，以便主程序動態加載

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ...kernel.registry import registered_routers
from ...utils.logger import logger

# 建立一個新的路由器，所有此模組的 API 都在這個路徑下
# 這會與 system_actions_router.py 中的前綴合併，FastAPI 能處理
router = APIRouter(
    prefix="/api/v1/actions",  # 使用 'actions' 以區分
    tags=["System Actions"],
)

class UIEvent(BaseModel):
    """定義前端 UI 事件的資料結構"""
    event_type: str  # e.g., "click", "change", "submit"
    component_id: str  # e.g., "run-pipeline-btn", "theme-toggle"
    details: dict = {}  # 可選的額外資訊

@router.post("/log_ui_event", status_code=200)
async def log_ui_event(event: UIEvent):
    """
    接收並記錄來自前端的使用者介面(UI)事件。
    """
    try:
        # 將所有結構化資訊格式化到 message 字串中
        log_message = f"UI Event '{event.event_type}' on component '{event.component_id}'."
        if event.details:
            log_message += f" Details: {str(event.details)}"

        # 使用 source 參數來標記事件來源
        await logger.log(
            level="INFO",
            message=log_message,
            source="UI_EVENT_LOGGER"
        )
        return {"status": "success", "message": "事件已成功記錄"}
    except Exception as e:
        # 如果日誌系統出錯，也要處理
        print(f"記錄UI事件時出錯: {e}")
        # 返回一個 HTTP 500 錯誤
        raise HTTPException(status_code=500, detail=f"無法記錄UI事件: {str(e)}")

# 將這個新的路由器註冊到全域列表中，以便 main.py 發現
registered_routers.append(router)

print("✅ 系統操作 (System Actions) 模組已成功加載並註冊路由。")
