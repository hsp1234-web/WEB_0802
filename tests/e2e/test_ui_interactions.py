# -*- coding: utf-8 -*-
# 繁體中文註解
import pytest
import subprocess
import time
import os
from playwright.sync_api import Page, expect, sync_playwright

# --- 設定 ---
# 從環境變數讀取，若無則使用預設值
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8000))
BASE_URL = f"http://{HOST}:{PORT}"

@pytest.fixture(scope="module")
def live_server():
    """
    pytest fixture: 在測試模組開始前啟動 FastAPI 伺服器，
    並在所有測試結束後將其關閉。
    """
    # 使用 uvicorn 啟動伺服器。CWD 是專案根目錄。
    # .venv 是由 uv 建立的
    venv_python = os.path.join(".venv", "bin", "python")
    command = [
        venv_python,
        "-m", "uvicorn",
        "src.phoenix_core.main:app",
        f"--host={HOST}",
        f"--port={PORT}",
        "--log-level=info",
    ]

    # 將伺服器日誌導向一個檔案，以便後續驗證
    log_file_path = "server_e2e_test.log"
    with open(log_file_path, "w") as log_file:
        process = subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT)

    # 等待伺服器啟動
    time.sleep(5)  # 給予足夠的時間讓伺服器啟動

    yield BASE_URL  # 測試將會使用這個 URL

    # 測試結束後清理
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    print("\n伺服器已關閉。")

def test_all_ui_interactions_and_logging(live_server, page: Page):
    """
    端對端測試:
    1. 瀏覽 wolf.html 頁面。
    2. 依序點擊頁面上的所有主要互動元件。
    3. (此測試不進行斷言，其目的是為了觸發後端日誌記錄)
    """
    print(f"正在連線至: {live_server}")
    page.goto(live_server, wait_until="networkidle")

    # 驗證頁面標題
    expect(page).to_have_title("善狼研究平台 v10.1 - 風險評估資料庫版")
    print("✅ 頁面標題正確。")

    # --- 定義要點擊的元件 ID 或選擇器 ---
        # 修正後的操作順序：先切換分頁，再點擊其內部元件
    interactions = [
            # 1. 通用元件
        {"id": "theme-toggle", "name": "主題切換"},
        {"id": "font-increase", "name": "放大字體"},
        {"id": "font-decrease", "name": "縮小字體"},

            # 2. 測試資料庫管理分頁內的互動
            {"selector": "div.tab[data-tab='db_management']", "name": "分頁 - 資料庫管理 (預設)"},
            {"id": "run-pipeline-btn", "name": "運行管線按鈕"},

            # 3. 測試音訊轉錄儀分頁內的互動
            {"selector": "div.tab[data-tab='transcription']", "name": "分頁 - 音訊轉錄儀"},
            {"id": "upload-area", "name": "音訊上傳區"},

            # 4. 點擊其餘所有分頁以確保日誌記錄
        {"selector": "div.tab[data-tab='shan']", "name": "分頁 - 週報深度覆盤"},
        {"selector": "div.tab[data-tab='snapshot']", "name": "分頁 - 市場數據總覽"},
        {"selector": "div.tab[data-tab='factors']", "name": "分頁 - 因子儲存庫"},
        {"selector": "div.tab[data-tab='lab']", "name": "分頁 - 策略回測中心"},
        {"selector": "div.tab[data-tab='system']", "name": "分頁 - 系統監控"},
    ]

    for interaction in interactions:
        try:
            target_id = interaction.get("id")
            target_selector = interaction.get("selector")
            name = interaction["name"]

            print(f"正在操作: {name}...")

            if target_id:
                page.locator(f"#{target_id}").click()
            elif target_selector:
                page.locator(target_selector).click()

            # 短暫等待，讓後端有時間處理請求和寫入日誌
            page.wait_for_timeout(300)

        except Exception as e:
            pytest.fail(f"操作 '{name}' 失敗: {str(e)}")

    print("\n✅ 所有 UI 互動操作已成功模擬執行。")
    print("下一步是手動或在下個測試步驟中，檢查 'server_e2e_test.log' 檔案中的日誌記錄。")
