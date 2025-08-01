import time
from pydantic import BaseModel

class StockData(BaseModel):
    symbol: str
    price: float
    timestamp: str

def get_stock_price_from_external_api(symbol: str) -> StockData:
    """
    模擬一個從外部 API 獲取股價的耗時操作。
    """
    print(f"模擬向外部 API 查詢 {symbol} 的股價...")
    # 思路框架: 故意延遲，以模擬真實世界的網路延遲。
    #           在真實的測試中，我們將會「跳過」這個延遲。
    time.sleep(2)
    print("...模擬查詢完成。")

    return StockData(
        symbol=symbol,
        price=2330.0, # 模擬價格
        timestamp="2025-08-02T12:00:00Z"
    )
