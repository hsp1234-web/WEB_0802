import pytest
import subprocess
import time
import requests
from playwright.sync_api import Page, expect

# 定義應用程式的基礎 URL
BASE_URL = "http://localhost:8080"

@pytest.fixture(scope="module", autouse=True)
def live_server_app():
    """
    一個在模組測試開始前自動運行的 fixture。
    它的職責是：
    1. 啟動完整的應用程式 (`./run.sh`)。
    2. 等待伺服器準備就緒。
    3. 在所有測試結束後，清理並終止應用程式進程。
    """
    process = None
    try:
        print("\n[UI Test Fixture] 正在啟動應用程式...")
        # 使用 Popen 在背景啟動 run.sh。
        # preexec_fn=os.setsid 讓我們可以終止整個進程組。
        process = subprocess.Popen(
            ["./run.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=__import__("os").setsid
        )

        # 等待伺服器啟動
        max_wait = 180  # 最長等待3分鐘
        start_time = time.time()
        server_ready = False
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{BASE_URL}/", timeout=1)
                if response.status_code == 200:
                    print("[UI Test Fixture] 伺服器已啟動並準備就緒！")
                    server_ready = True
                    break
            except requests.ConnectionError:
                time.sleep(1)

        if not server_ready:
            # 如果伺服器未能啟動，讀取其日誌並引發錯誤
            logs = process.communicate()[0]
            pytest.fail(f"伺服器在 {max_wait} 秒內未能啟動。日誌:\n{logs}")

        # 一旦伺服器準備好，就將控制權交給測試
        yield

    finally:
        # 測試結束後，終止進程
        if process:
            print("\n[UI Test Fixture] 正在終止應用程式...")
            # 使用 os.killpg 來終止整個進程組
            __import__("os").killpg(__import__("os").getpgid(process.pid), __import__("signal").SIGTERM)
            try:
                # 等待進程終止
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("[UI Test Fixture] 進程終止超時，強制終止。")
                __import__("os").killpg(__import__("os").getpgid(process.pid), __import__("signal").SIGKILL)
            print("[UI Test Fixture] 應用程式已終止。")

def test_transcription_upload_and_status(page: Page):
    """
    測試完整的 UI 流程：
    1. 導航到首頁，切換到轉錄儀分頁。
    2. 上傳一個音訊檔案。
    3. 驗證日誌容器中是否出現了任務 ID。
    """
    page.goto(BASE_URL)

    # 點擊「音訊轉錄儀」分頁以確保它是可見的
    page.click("div[data-tab='transcription']")

    # 注入日誌標記
    page.evaluate("console.log('TEST: 即將上傳音訊檔案...')")

    # 找到檔案輸入元素並上傳我們的虛擬檔案
    # 這個操作會自動觸發上傳流程，無需額外點擊
    file_input_selector = "input#file-input"
    page.set_input_files(file_input_selector, "tests/dummy_audio_for_ui_test.wav")

    # 等待並驗證結果
    # 上傳後，日誌容器中應出現包含 "任務ID" 的條目
    log_container_selector = "div#log-container"
    task_id_locator = page.locator(log_container_selector).locator("text=/任務ID:/")

    # 使用 expect 等待元素可見
    expect(task_id_locator).to_be_visible(timeout=30000)

    # 獲取任務 ID 並打印
    task_id_text = task_id_locator.first.inner_text()
    print(f"\n[UI Test] 在頁面上找到任務 ID: {task_id_text}")

    # 注入另一個日誌標記
    page.evaluate(f"console.log('TEST: 成功找到任務 ID: {task_id_text}')")
