# 檔案: src/phoenix_core/main.py (更新版)
import pkgutil
import importlib
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from .kernel.settings import settings
# 思路框架: 導入我們新建立的註冊中心中的 registered_routers 列表。
from .kernel.registry import registered_routers
# 導入我們自己的 modules 套件
from . import modules

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="一個採用模組化單體架構的高效能後端服務。",
)

# --- 自動模組加載 ---
# 思路框架: 這段代碼會自動掃描 `phoenix_core.modules` 套件下的所有子模組。
#           無論未來新增多少模組，只要放在該目錄下，都會被自動導入。
#           導入模組時，其 __init__.py 中的註冊碼就會執行。
def discover_and_load_modules():
    print("--- 開始自動探索模組 ---")
    module_path = modules.__path__
    module_prefix = f"{modules.__name__}."
    for _, name, _ in pkgutil.iter_modules(module_path, module_prefix):
        print(f"發現模組: {name}，正在導入...")
        importlib.import_module(name)
    print("--- 所有模組探索完畢 ---")

# --- 掛載路由 ---
# 思路框架: 在應用啟動時，先執行模組探索，然後將所有註冊的路由掛載到主應用上。
@app.on_event("startup")
def startup_event():
    discover_and_load_modules()
    print("--- 開始掛載已註冊的路由 ---")
    for router in registered_routers:
        app.include_router(router)
    print("--- 所有路由掛載完畢 ---")


# --- 基礎 API 端點 ---
# 獲取專案根目錄 (假設 main.py 在 src/phoenix_core/ 內)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 掛載根目錄為靜態文件夾，這樣 HTML 裡面的相對路徑 (如 CSS/JS) 才能正確載入
app.mount("/static", StaticFiles(directory=PROJECT_ROOT), name="static")

@app.get("/", response_class=FileResponse, tags=["系統 (System)"])
async def read_root():
    """提供 wolf.html 儀表板作為主頁面。"""
    return os.path.join(PROJECT_ROOT, 'wolf.html')

@app.get("/system/config", tags=["系統 (System)"])
async def get_system_config():
    return {"app_name": settings.APP_NAME, "environment": settings.APP_ENV}
