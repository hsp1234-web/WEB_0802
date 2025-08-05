# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🎭 test_button_click.py (E2E Playwright Test) - v5              ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 在一個隔離、可控的環境中，使用 Playwright 執行真實的     ║
# ║           前端點擊測試，並驗證後端反應。                           ║
# ║   - 核心: venv, pip, Programmatic Uvicorn, Playwright, Watchdog    ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
import asyncio
import time
from datetime import datetime

# --- 路徑設定 ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

# --- 全域設定 (Global Settings) ---
VENV_DIR = os.path.join(project_root, ".venv_e2e_test")
SERVER_READY_TIMEOUT = 30

VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_header(title):
    print("\n" + "="*80)
    print(f"🎭 {get_timestamp()} - {title}")
    print("="*80)

def run_sync_command(command, cwd=".", env=None):
    print(f"   🔹 執行命令: {' '.join(command)} (於 {cwd})")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        cwd=cwd,
        env=env
    )
    for line in process.stdout:
        print(f"     [CMD_OUT] {line.strip()}")

    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    print(f"   ✅ 命令成功完成。")

async def playwright_test_runner(server) -> bool:
    from playwright.async_api import async_playwright, expect

    print_header("執行 Playwright UI 互動測試")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.on("console", lambda msg: print(f"    [BROWSER_CONSOLE] {msg.text}"))

            print("   [Playwright] 導航至 http://127.0.0.1:8080")
            await page.goto("http://127.0.0.1:8080", timeout=15000, wait_until="networkidle")

            await expect(page.get_by_role("heading", name="鳳凰之心")).to_be_visible(timeout=5000)
            print("   [Playwright] ✅ 頁面載入成功。")

            run_button_selector = "#db-management-panel .btn-primary"
            print(f"   [Playwright] 模擬點擊按鈕: '{run_button_selector}'")
            await page.click(run_button_selector)
            print("   [Playwright] ✅ 已點擊按鈕。")

            log_area = page.locator("#system-log-content")
            expected_text = "開始執行管線..."
            await expect(log_area).to_contain_text(expected_text, timeout=5000)
            print(f"   [Playwright] ✅ 成功驗證到文字: '{expected_text}'")

            await browser.close()
            test_passed = True
    except Exception as e:
        print(f"   [Playwright] ❌ 測試失敗: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        test_passed = False
    finally:
        print("   [E2E] 測試執行完畢，正在發出伺服器關閉信號...")
        server.should_exit = True
        return test_passed

async def main_async():
    import uvicorn
    from phoenix_core.main import app
    from phoenix_core.database import db_manager
    from phoenix_core.watchdog import HEARTBEAT_KEY

    print_header("步驟 4: 以程式化方式啟動核心應用程式")
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info", lifespan="on")
    server = uvicorn.Server(config)

    async def watchdog():
        start_time = time.monotonic()
        while time.monotonic() - start_time < SERVER_READY_TIMEOUT:
            try:
                if await asyncio.to_thread(db_manager.get_status, HEARTBEAT_KEY):
                    print(f"   [Watchdog] ✅ 偵測到心跳！伺服器已就緒。")
                    return
            except Exception: pass
            await asyncio.sleep(1)
        print(f"   [Watchdog] ❌ 錯誤: 等待伺服器心跳超時 ({SERVER_READY_TIMEOUT}秒)！", file=sys.stderr)
        server.should_exit = True

    server_task = asyncio.create_task(server.serve())
    watchdog_task = asyncio.create_task(watchdog())

    await watchdog_task

    if server.should_exit:
        raise RuntimeError("伺服器因看門狗超時而未能啟動。")

    test_result = await playwright_test_runner(server)
    await server_task

    if not test_result:
        raise RuntimeError("Playwright 測試案例失敗。")

def main():
    start_time = time.time()
    os.environ["PYTHONUNBUFFERED"] = "1"

    try:
        if os.path.isdir(VENV_DIR):
            print_header(f"偵測到舊的 E2E 虛擬環境，正在刪除以確保乾淨的測試環境...")
            shutil.rmtree(VENV_DIR)

        print_header(f"步驟 1: 建立 Python 虛擬環境 ({VENV_DIR})")
        run_sync_command([sys.executable, "-m", "venv", VENV_DIR], cwd=project_root)

        print_header("步驟 2: 在 venv 中安裝所有開發依賴 (使用 pip)")
        # **關鍵修復**: 放棄使用 uv，改用標準的 pip 並禁用快取，以獲得最大相容性
        install_command = [
            VENV_PIP, "install", "--no-cache-dir",
            "-r", os.path.join(project_root, 'requirements/dev.txt')
        ]
        run_sync_command(install_command, cwd=project_root)

        print_header("步驟 3: 安裝 Playwright 瀏覽器二進位檔案")
        run_sync_command([VENV_PYTHON, "-m", "playwright", "install", "--with-deps"], cwd=project_root)

        print_header("準備進入異步測試階段...")
        run_sync_command([VENV_PYTHON, __file__, "--run-async"], cwd=project_root)

        print_header("🎉 E2E 測試成功完成！ 🎉")

    except (subprocess.CalledProcessError, RuntimeError) as e:
        print(f"\n❌ E2E 測試流程失敗: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        end_time = time.time()
        print("\n" + "="*80)
        print(f"🏁 E2E 測試流程結束，總耗時: {end_time - start_time:.2f} 秒。")
        print("="*80)

if __name__ == "__main__":
    if "--run-async" in sys.argv:
        asyncio.run(main_async())
    else:
        main()
