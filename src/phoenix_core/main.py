# 檔案: src/phoenix_core/main.py (V36 - 動態加載版)
import pkgutil
import importlib
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import asyncio

from .kernel.settings import settings
from .kernel.registry import registered_routers
from . import modules
from .background import worker
from .database import db_manager

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="一個採用模組化單體架構的高效能後端服務。",
)

# 用一個集合來追蹤已加載的模組和已註冊的路由，以支援動態重載
loaded_module_names = set()
registered_router_prefixes = set()

def discover_and_load_modules(reload=False):
    """
    探索並加載 `modules` 目錄下的所有模組。
    支援在服務運行時進行重載（只加載新模組）。
    """
    global loaded_module_names, registered_router_prefixes

    if reload:
        print("--- 開始重新掃描並加載新模組 ---")
    else:
        print("--- 開始自動探索模組 ---")
        loaded_module_names.clear()
        registered_router_prefixes.clear()

    module_path = modules.__path__
    module_prefix = f"{modules.__name__}."

    # 探索模組
    for _, name, _ in pkgutil.iter_modules(module_path, module_prefix):
        if name not in loaded_module_names:
            print(f"發現新模組: {name}，正在導入...")
            importlib.import_module(name)
            loaded_module_names.add(name)

    # 掛載新的路由
    new_routers_found = False
    for router in registered_routers:
        router_id = router.prefix
        if router_id not in registered_router_prefixes:
            print(f"發現新路由: {router.tags[0] if router.tags else router_id}，正在掛載...")
            app.include_router(router)
            registered_router_prefixes.add(router_id)
            new_routers_found = True

    if reload and not new_routers_found:
        print("--- 未發現需要加載的新模組/路由 ---")

    print("--- 模組加載流程結束 ---")

@app.on_event("startup")
async def startup_event():
    # 首次啟動時，加載所有模組
    discover_and_load_modules(reload=False)

    # 使用背景工作管理器來啟動所有任務
    worker.start_background_tasks()

    # 寫入啟動日誌
    db_manager.write_log("INFO", "核心服務啟動成功。")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
app.mount("/static", StaticFiles(directory=PROJECT_ROOT), name="static")

@app.get("/", response_class=FileResponse, tags=["系統 (System)"])
async def read_root():
    """提供 wolf.html 儀表板作為主頁面。"""
    return os.path.join(PROJECT_ROOT, 'wolf.html')

@app.get("/system/config", tags=["系統 (System)"])
async def get_system_config():
    return {"app_name": settings.APP_NAME, "environment": settings.APP_ENV}
