# -*- coding: utf-8 -*-
# 檔案: tests/e2e/test_ui_interaction.py
# 說明: 一個自包含的、一次性的全自動化 E2E 測試器。
#      用於驗證前端 UI 互動到後端響應的完整流程。

import sys
import os
import subprocess
import time
from datetime import datetime, timedelta
import asyncio
import shutil

# --- 全域設定 ---
VENV_DIR = ".venv_e2e"
VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")
TEST_TIMEOUT = 60
SERVER_LOG_FILE = "server_e2e.log"

def print_header(title):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*80)
    print(f"🚀 {timestamp} - {title}")
    print("="*80)

def run_setup_command(command, cwd="."):
    print(f"   🔹 執行設定命令: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd, check=False)
    if result.returncode != 0:
        print("❌ 設定命令失敗:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"命令 {' '.join(command)} 執行失敗。")
    print("   ✅ 命令成功完成。")

async def server_watchdog(server_process, log_file):
    last_log_time = datetime.now()
    print_header("看門狗已啟動 (15秒無日誌則超時)")
    while True:
        if server_process.poll() is not None:
            print("   [看門狗] 監測到伺服器進程已結束。")
            break

        if datetime.now() - last_log_time > timedelta(seconds=15):
            print("   [看門狗] ❌ 偵測到伺服器在15秒內無任何日誌輸出！", file=sys.stderr)
            server_process.terminate()
            raise asyncio.TimeoutError("伺服器日誌超時")

        if os.path.exists(log_file):
            try:
                current_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if current_mtime > last_log_time:
                    last_log_time = current_mtime
            except FileNotFoundError:
                pass

        await asyncio.sleep(1)

async def run_playwright_test():
    from playwright.async_api import async_playwright, expect

    print_header("第二階段：執行 Playwright 互動測試")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"   [瀏覽器日誌] {msg.text}"))

        print("   🔹 正在訪問服務頁面: http://127.0.0.1:8080")
        await page.goto("http://127.0.0.1:8080", wait_until="networkidle")

        print("   🔹 模擬點擊 '運行' 按鈕...")
        await page.locator("text=運行").click()

        print("   🔹 正在驗證結果...")
        log_output_locator = page.locator("#system-log-content")

        await expect(log_output_locator).to_contain_text("開始運行管線", timeout=10000)

        print("   ✅ 驗證成功！")
        await browser.close()
        return True

def run_core_logic():
    server_process = None
    try:
        print_header("啟動後端伺服器")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.abspath("src") + os.pathsep + env.get("PYTHONPATH", "")

        server_command = [VENV_PYTHON, "-m", "uvicorn", "phoenix_core.main:app", "--host", "0.0.0.0", "--port", "8080"]
        with open(SERVER_LOG_FILE, "w") as log_file:
            server_process = subprocess.Popen(server_command, stdout=log_file, stderr=subprocess.STDOUT, env=env)

        time.sleep(8)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        main_task = loop.create_task(run_playwright_test())
        watchdog_task = loop.create_task(server_watchdog(server_process, SERVER_LOG_FILE))

        done, pending = loop.run_until_complete(asyncio.wait([main_task, watchdog_task], return_when=asyncio.FIRST_COMPLETED))

        test_passed = any(task == main_task and task.result() for task in done)

        if not test_passed:
            raise RuntimeError("Playwright 測試未通過或看門狗超時。")

        print("\n" + "="*40 + "\n✅ E2E 測試成功！健康碼已生成。\n" + "="*40)
        time.sleep(5)

    finally:
        if server_process and server_process.poll() is None:
            print("   正在清理並關閉後端伺服器...")
            server_process.terminate()
            server_process.wait()
            print("   ✅ 伺服器已關閉。")

def main():
    if "--run-in-venv" in sys.argv:
        run_core_logic()
        return

    print_header("第一階段：準備 E2E 測試環境")
    if os.path.exists(VENV_DIR):
        print(f"   移除舊的虛擬環境 {VENV_DIR}...")
        shutil.rmtree(VENV_DIR)

    print(f"   創建新的虛擬環境於: {VENV_DIR}")
    run_setup_command([sys.executable, "-m", "venv", VENV_DIR])

    run_setup_command([os.path.join(VENV_DIR, "bin", "pip"), "install", "uv"])

    uv_command = [os.path.join(VENV_DIR, "bin", "uv"), "pip", "install", "--python", VENV_PYTHON]
    run_setup_command(uv_command + ["-r", "requirements/base.txt"])
    run_setup_command(uv_command + ["-r", "requirements/dev.txt"])
    run_setup_command(uv_command + ["-e", "."])

    run_setup_command([os.path.join(VENV_DIR, "bin", "playwright"), "install", "--with-deps"])

    print_header("準備在 venv 中執行核心測試邏輯")
    relaunch_command = [VENV_PYTHON, __file__, "--run-in-venv"]

    try:
        subprocess.run(relaunch_command, check=True, timeout=TEST_TIMEOUT)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print(f"\n❌ 核心測試邏輯執行失敗或超時。", file=sys.stderr)
        print("="*80)
        print("🕵️  正在讀取伺服器日誌以進行偵錯...")
        print("="*80)
        if os.path.exists(SERVER_LOG_FILE):
            with open(SERVER_LOG_FILE, "r") as f:
                print(f.read())
        else:
            print("   伺服器日誌檔案 'server_e2e.log' 未找到。", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
