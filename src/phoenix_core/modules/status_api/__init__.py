# 檔案: src/phoenix_core/modules/status_api/__init__.py
from ...kernel.registry import register_router
from .router import router

# 將本模組的 router 實例，註冊到核心引擎的註冊中心。
register_router(router)
