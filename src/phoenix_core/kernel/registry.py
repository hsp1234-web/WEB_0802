# 檔案: src/phoenix_core/kernel/registry.py
from fastapi import APIRouter
from typing import List

# 思路框架: 建立一個全域的列表，專門用來存放所有模組的 APIRouter。
#           這是我們所有模組與主應用溝通的唯一橋樑。
registered_routers: List[APIRouter] = []

def register_router(router: APIRouter):
    """
    提供給各個功能模組用來註冊其 API 路由的函式。
    """
    print(f"正在註冊路由: {router.prefix}...")
    registered_routers.append(router)
