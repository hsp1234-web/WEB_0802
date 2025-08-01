import pytest
from fastapi.testclient import TestClient

# 我們將模擬 storage 模組的行為。
# 這個路徑指向 logic.py 檔案中導入的 storage 模組的引用。
MODULE_PATH_TO_MOCK = "phoenix_core.modules.dataprovider.logic.storage"

@pytest.mark.timeout(1)
def test_stock_data_cache_hit(monkeypatch):
    """測試快取命中的場景 (不應有延遲)。"""
    # 準備: 模擬 storage.load_json，讓它返回一個預設的快取數據。
    def mock_load_json(file_name):
        return {"symbol": "TSMC", "price": 123.45, "timestamp": "cached_time"}

    monkeypatch.setattr(f"{MODULE_PATH_TO_MOCK}.load_json", mock_load_json)

    # 延遲匯入 app，確保修補在 app 載入前生效。
    from phoenix_core.main import app

    # 執行與斷言
    with TestClient(app) as client:
        response = client.get("/data/stock/TSMC")
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 123.45 # 驗證返回的是快取數據
        assert data["timestamp"] == "cached_time"

@pytest.mark.timeout(1)
def test_stock_data_cache_miss(monkeypatch):
    """測試快取未命中的場景 (應有延遲，但我們也會模擬掉)。"""
    # 準備: 模擬 load_json 返回 None，並模擬 save_json 不做任何事。
    monkeypatch.setattr(f"{MODULE_PATH_TO_MOCK}.load_json", lambda fn: None)
    monkeypatch.setattr(f"{MODULE_PATH_TO_MOCK}.save_json", lambda fn, data: None)
    # 為了讓測試快速，我們也必須模擬掉 time.sleep
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    # 延遲匯入 app
    from phoenix_core.main import app

    # 執行與斷言
    with TestClient(app) as client:
        response = client.get("/data/stock/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["price"] == 2330.0 # 驗證返回的是新生成的數據
