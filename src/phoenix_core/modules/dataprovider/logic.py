import time
import datetime
from pydantic import BaseModel
# 思路框架: 導入我們在 kernel 中新建的存儲服務函式。
from ...kernel import storage

class StockData(BaseModel):
    symbol: str
    price: float
    timestamp: str

def get_stock_price(symbol: str) -> StockData:
    """
    獲取股價。優先從快取（檔案系統）讀取，若無快取則模擬從外部 API 獲取。
    """
    # 1. 嘗試從快取讀取
    cached_data = storage.load_json(f"stock_{symbol}")
    if cached_data:
        print(f"從快取命中讀取 {symbol} 的數據。")
        return StockData(**cached_data)

    # 2. 快取未命中，模擬從外部 API 獲取
    print(f"快取未命中。模擬向外部 API 查詢 {symbol} 的股價...")
    time.sleep(2) # 模擬網路延遲

    new_data = StockData(
        symbol=symbol,
        price=2330.0,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    # 3. 將新數據寫入快取
    storage.save_json(f"stock_{symbol}", new_data.model_dump())

    return new_data
