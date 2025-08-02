# -*- coding: utf-8 -*-
# 檔案: tests/integration/test_colab_flow.py (V2 - Fixture 驅動版)
# 說明: 驗證 Colab 啟動流程的整合測試。
#       此版本已重構，使用來自 conftest.py 的共享 Fixture。

import httpx

# --- 常數設定 ---
# 注意: 這些常數現在也可以考慮移至 conftest.py，以實現更高層次的共享
API_STATUS_URL = "http://localhost:8088/api/v1/status"

def test_colab_api_status_endpoint(live_api_service):
    """
    【已簡化】
    測試在 Colab 流程啟動後，其後端 API 的 /api/v1/status 端點是否正常運作。

    這個測試函式現在非常乾淨，它只關心一件事：
    在 `live_api_service` Fixture 確保服務已就緒的前提下，驗證 API 的回應是否正確。
    所有關於如何啟動、等待、關閉服務的複雜邏輯都已被抽象到 Fixture 中。
    """
    print("\n--- 執行測試: test_colab_api_status_endpoint ---")

    # 1. 發送請求
    #    此時，我們 100% 確定服務已經在背景成功運行
    print(f"   - 正在請求 API: {API_STATUS_URL}")
    with httpx.Client() as client:
        response = client.get(API_STATUS_URL)

    # 2. 驗證狀態碼
    assert response.status_code == 200
    print(f"   - ✅ 狀態碼為 200，請求成功。")

    # 3. 驗證回傳的 JSON 結構
    print(f"   - 正在驗證 JSON 結構...")
    data = response.json()
    assert "status" in data
    assert "logs" in data
    assert "action_url" in data
    assert "current_stage" in data["status"]
    assert "cpu_usage" in data["status"]
    assert "ram_usage" in data["status"]
    assert "apps_status" in data["status"]
    print(f"   - ✅ JSON 結構驗證通過。")

    # 4. 打印部分回傳內容以供參考
    print(f"   - 後端回傳的當前階段: {data['status']['current_stage']}")
    print(f"   - 後端日誌數量: {len(data['logs'])}")
    print("--- 測試執行完畢 ---")
