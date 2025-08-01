# 檔案: src/phoenix_core/main.py
from fastapi import FastAPI
# 思路框架: 從 kernel 導入我們的設定實例。
from .kernel.settings import settings

# 使用 settings 中的值來動態設定應用程式標題和版本
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="一個採用模組化單體架構的高效能後端服務。",
)

@app.get("/", tags=["系統 (System)"])
async def read_root():
    """
    根節點，用於基礎的健康檢查。
    """
    return {"status": "OK", "message": f"歡迎來到 {settings.APP_NAME}！"}

# 思路框架: 建立一個新的端點，專門用來驗證設定是否被成功載入。
#           這為我們提供了一個清晰的驗證目標。
@app.get("/system/config", tags=["系統 (System)"])
async def get_system_config():
    """
    讀取並顯示當前的部分系統設定（出於安全考量，不應顯示敏感資訊）。
    """
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
