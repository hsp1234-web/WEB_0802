# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import time
import pytest
import httpx

# --- 測試設定 ---
COLAB_RUNNER_SCRIPT = "run/colab_runner.py"
API_STATUS_URL = "http://localhost:8088/api/v1/status"
STARTUP_WAIT_SECONDS = 25  # 給予足夠的時間讓 venv 建立和依賴安裝
POLL_INTERVAL_SECONDS = 1

@pytest.fixture(scope="module")
def colab_backend_service():
    """
    一個 Pytest Fixture，負責在背景啟動 Colab 後端服務，
    並在測試結束後將其關閉。
    """
    # 檢查腳本是否存在
    if not os.path.exists(COLAB_RUNNER_SCRIPT):
        pytest.fail(f"找不到 Colab 啟動腳本: {COLAB_RUNNER_SCRIPT}")

    print(f"\n--- 啟動背景服務: {COLAB_RUNNER_SCRIPT} ---")
    # 使用 Popen 啟動 colab_runner.py，它會再啟動 start_api_service.py
    process = subprocess.Popen(
        [sys.executable, COLAB_RUNNER_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # 合併輸出方便除錯
        text=True,
        encoding='utf-8'
    )

    # --- 等待服務啟動 ---
    # 我們將輪詢 API 端點，直到它成功回傳 200 或超時
    start_time = time.time()
    service_ready = False
    while time.time() - start_time < STARTUP_WAIT_SECONDS:
        try:
            # 將後端日誌打印出來，以監控啟動過程
            # 注意：這裡使用 non-blocking read 可能會更複雜，暫時簡化
            # for line in process.stdout:
            #     print(f"  [SERVICE LOG] {line.strip()}")

            with httpx.Client() as client:
                response = client.get(API_STATUS_URL, timeout=POLL_INTERVAL_SECONDS)
                if response.status_code == 200:
                    print(f"\n✅ 服務在 {time.time() - start_time:.2f} 秒後成功啟動。")
                    service_ready = True
                    break
        except (httpx.ConnectError, httpx.ReadTimeout):
            # 服務尚未就緒，這是預期中的
            print(f"   - 等待服務啟動... (已過 {time.time() - start_time:.0f}s)")
            time.sleep(POLL_INTERVAL_SECONDS)

    if not service_ready:
        # 如果服務啟動失敗，結束測試前先殺掉進程並打印日誌
        process.terminate()
        out, _ = process.communicate()
        print("❌ 服務啟動超時。後端日誌輸出:")
        print(out)
        pytest.fail("後端 API 服務未能在指定時間內啟動。")

    # 使用 yield 將控制權交還給測試函式
    yield process

    # --- 測試結束後的清理工作 ---
    print(f"\n--- 測試結束，正在關閉背景服務 (PID: {process.pid}) ---")
    process.terminate()
    try:
        process.wait(timeout=5)
        print("✅ 服務已成功關閉。")
    except subprocess.TimeoutExpired:
        print("⚠️ 服務關閉超時，強制終止。")
        process.kill()

def test_colab_api_status_endpoint(colab_backend_service):
    """
    測試在 Colab 流程啟動後，其後端 API 的 /api/v1/status 端點是否正常運作。
    """
    print("\n--- 執行測試: test_colab_api_status_endpoint ---")

    # 1. 發送請求
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
