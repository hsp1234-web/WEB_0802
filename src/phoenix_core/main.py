# 檔案: src/phoenix_core/main.py (更新版)
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
from .background.tasks import periodic_heartbeat
from .database import db_manager

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="一個採用模組化單體架構的高效能後端服務。",
)

def discover_and_load_modules():
    print("--- 開始自動探索模組 ---")
    module_path = modules.__path__
    module_prefix = f"{modules.__name__}."
    for _, name, _ in pkgutil.iter_modules(module_path, module_prefix):
        print(f"發現模組: {name}，正在導入...")
        importlib.import_module(name)
    print("--- 所有模組探索完畢 ---")

@app.on_event("startup")
async def startup_event():
    discover_and_load_modules()
    print("--- 開始掛載已註冊的路由 ---")
    for router in registered_routers:
        app.include_router(router)
    print("--- 所有路由掛載完畢 ---")

    # 啟動背景心跳任務
    asyncio.create_task(periodic_heartbeat())

    # 在啟動時寫入一些測試日誌，以供 debug_ALL.py 驗證
    print("--- 寫入啟動日誌以供參數驗證 ---")
    db_manager.write_log("INFO", "這是一條 INFO 日誌")
    db_manager.write_log("ERROR", "這是一條 ERROR 日誌")
    db_manager.write_log("BATTLE", "這是一條 BATTLE 日誌")
    db_manager.write_log("LOG_SHELL", "這是一條 LOG_SHELL 日誌")
    db_manager.write_log("CMD", "這是一條 CMD 日誌")
    db_manager.write_log("SUCCESS", "這是一條 SUCCESS 日誌")
    db_manager.write_log("CRITICAL", "這是一條 CRITICAL 日誌")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
app.mount("/static", StaticFiles(directory=PROJECT_ROOT), name="static")

@app.get("/", response_class=FileResponse, tags=["系統 (System)"])
async def read_root():
    """提供 wolf.html 儀表板作為主頁面。"""
    return os.path.join(PROJECT_ROOT, 'wolf.html')

@app.get("/system/config", tags=["系統 (System)"])
async def get_system_config():
    return {"app_name": settings.APP_NAME, "environment": settings.APP_ENV}
