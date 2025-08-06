# -*- coding: utf-8 -*-
# 這是普羅米修斯管線模組的入口點。
# 當主應用程式探索模組時，這個檔案會被執行。

from src.phoenix_core.kernel.registry import register_router
from .router import router

# 將此模組的 API 路由器註冊到主應用程式中
register_router(router)

print("✅ 普羅米修斯管線 (Prometheus Pipeline) 模組已成功加載並註冊路由。")
