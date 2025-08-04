import time
import datetime
from pydantic import BaseModel
from ...kernel import storage
from ...utils.logger import logger

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
        logger.log("INFO", f"從快取命中讀取 {symbol} 的數據。", source="dataprovider")
        return StockData(**cached_data)

    # 2. 快取未命中，模擬從外部 API 獲取
    logger.log("INFO", f"快取未命中。模擬向外部 API 查詢 {symbol} 的股價...", source="dataprovider")
    time.sleep(2) # 模擬網路延遲

    new_data = StockData(
        symbol=symbol,
        price=2330.0,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    # 3. 將新數據寫入快取
    storage.save_json(f"stock_{symbol}", new_data.model_dump())

    return new_data
