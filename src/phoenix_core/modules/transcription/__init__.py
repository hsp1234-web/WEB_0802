# src/phoenix_core/modules/transcription/__init__.py

# 導入 router 模組，確保在應用啟動時，其中的 @register_router 修飾器會被執行。
# 這使得主程式的 `discover_and_load_modules` 函式能夠自動探索並掛載此模組的 API 路由。
from . import router
