# 檔案: src/phoenix_core/modules/dataprovider/__init__.py

# 思路框架: 這是實現「插件化」的關鍵。
#           當 Python 導入這個模組時，這段程式碼會自動執行。
from ...kernel.registry import register_router
from .router import router

# 將本模組的 router 實例，註冊到核心引擎的註冊中心。
register_router(router)
