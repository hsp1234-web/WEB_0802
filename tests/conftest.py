# -*- coding: utf-8 -*-
# 檔案: tests/conftest.py
# 說明: Pytest 的公共測試配置文件。
#       在此處定義的 Fixture 可被所有測試案例共享。

import sys
import os
import subprocess
import time
import pytest
import httpx

# --- 常數設定 ---
# 將測試目標和設定集中管理
COLAB_RUNNER_SCRIPT = "run/colab_runner.py"
API_STATUS_URL = "http://localhost:8088/api/v1/status"
STARTUP_WAIT_SECONDS = 30  # 延長等待時間以應對較慢的 CI 環境
POLL_INTERVAL_SECONDS = 1

@pytest.fixture(scope="module")
def live_api_service():
    """
    【可複用的測試裝置 (Fixture)】

    職責:
    1. 在背景啟動一個完整的、由 Colab 驅動的後端 API 服務。
    2. 輪詢其健康檢查端點，直到服務就緒或超時。
    3. 將啟動的服務進程 (process) 物件 `yield` 給測試函式使用。
    4. 在所有使用此 Fixture 的測試結束後，自動終止服務進程。

    使用方法:
    任何測試函式只要在參數中包含 `live_api_service`，
    Pytest 就會自動在該測試執行前，為其準備好一個正在運行的後端服務。
    """
    # 檢查腳本是否存在
    if not os.path.exists(COLAB_RUNNER_SCRIPT):
        pytest.fail(f"找不到 Colab 啟動腳本: {COLAB_RUNNER_SCRIPT}")

    print(f"\n--- [Fixture] 正在啟動背景服務: {COLAB_RUNNER_SCRIPT} ---")

    # 使用 Popen 啟動 colab_runner.py
    process = subprocess.Popen(
        [sys.executable, COLAB_RUNNER_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8'
    )

    # --- 等待服務啟動 (Health Check) ---
    start_time = time.time()
    service_ready = False
    while time.time() - start_time < STARTUP_WAIT_SECONDS:
        try:
            with httpx.Client() as client:
                response = client.get(API_STATUS_URL, timeout=POLL_INTERVAL_SECONDS)
                if response.status_code == 200:
                    print(f"\n✅ [Fixture] 服務在 {time.time() - start_time:.2f} 秒後成功啟動。")
                    service_ready = True
                    break
        except (httpx.ConnectError, httpx.ReadTimeout):
            print(f"   - [Fixture] 等待服務啟動... (已過 {time.time() - start_time:.0f}s)")
            time.sleep(POLL_INTERVAL_SECONDS)

    if not service_ready:
        process.terminate()
        out, _ = process.communicate()
        print("❌ [Fixture] 服務啟動超時。後端日誌輸出:")
        print(out)
        pytest.fail("後端 API 服務未能在指定時間內啟動。")

    # 使用 yield 將控制權和進程物件交還給測試函式
    yield process

    # --- 清理工作 (Teardown) ---
    print(f"\n--- [Fixture] 測試結束，正在關閉背景服務 (PID: {process.pid}) ---")
    process.terminate()
    try:
        process.wait(timeout=5)
        print("✅ [Fixture] 服務已成功關閉。")
    except subprocess.TimeoutExpired:
        print("⚠️ [Fixture] 服務關閉超時，強制終止。")
        process.kill()
