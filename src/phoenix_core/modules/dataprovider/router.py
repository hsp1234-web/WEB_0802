from fastapi import APIRouter
# 思路框架: 更新導入的函式名稱。
from .logic import get_stock_price, StockData

router = APIRouter(
    prefix="/data",
    tags=["數據提供者 (Data Provider)"],
)

# ... 保留 /status 端點 ...
@router.get("/status", summary="檢查數據提供者模組狀態")
async def get_dataprovider_status():
    return {"status": "active", "message": "Data Provider is ready."}


@router.get("/stock/{symbol}", response_model=StockData, summary="獲取股票數據（具備快取）")
async def get_stock_data(symbol: str):
    """
    從數據提供者獲取特定股票的數據。
    此端點具備檔案快取功能。
    """
    return get_stock_price(symbol)
