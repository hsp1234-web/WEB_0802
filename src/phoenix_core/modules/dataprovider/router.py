# 檔案: src/phoenix_core/modules/dataprovider/router.py (更新版)
from fastapi import APIRouter
# 思路框架: 導入新建的 logic 函式和 Pydantic 模型。
from .logic import get_stock_price_from_external_api, StockData

router = APIRouter(
    prefix="/data",
    tags=["數據提供者 (Data Provider)"],
)

# ... 保留原有的 /status 端點 ...
@router.get("/status", summary="檢查數據提供者模組狀態")
async def get_dataprovider_status():
    return {"status": "active", "message": "Data Provider is ready."}

# 思路框架: 建立一個新的、有意義的 API 端點。
#           它的回應模型由 logic 層的 StockData 強制約束。
@router.get("/stock/{symbol}", response_model=StockData, summary="獲取模擬股票數據")
async def get_stock_data(symbol: str):
    """
    從數據提供者獲取特定股票的數據。
    (目前為模擬數據)
    """
    return get_stock_price_from_external_api(symbol)
