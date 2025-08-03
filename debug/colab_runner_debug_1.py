# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 後端健康檢查腳本 (Backend Health Checker) V1.0               ║
# ║         (檔案: colab_runner_debug_1.py)                              ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 根據 `BUG.MD` 的穩健設計原則，在本地環境中，以一個      ║
# ║           獨立、可重現的方式，測試後端服務的健康狀況。             ║
# ║   - 核心功能:                                                      ║
# ║       1. 建立獨立的虛擬環境 (`.venv_debug`)。                    ║
# ║       2. 安裝必要的開發依賴。                                    ║
# ║       3. 啟動核心後端服務 (Uvicorn)。                              ║
# ║       4. 實作看門狗 (Watchdog) 機制，監控服務活性。                ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import threading
import time
import shutil
from pathlib import Path

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    print("\n" + "="*80)
    print(f"🚀 {time.strftime('%Y-%m-%d %H:%M:%S')} - {title}")
    print("="*80)

# --- 全域設定 ---
VENV_DIR = Path("./.venv_debug")
VENV_PYTHON = VENV_DIR / "bin" / "python"
REQUIREMENTS_FILE = Path("./requirements/dev.txt")
WATCHDOG_TIMEOUT = 30.0  # 秒，給予啟動較寬裕的時間

def run_command(command, cwd=".", check=True):
    """
    執行一個子程序命令，為了日誌清晰，我們分別捕獲並打印標準輸出和標準錯誤。
    """
    print(f"   🔹 執行命令: {' '.join(map(str, command))}")
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(cwd),
            check=check
        )
        if process.stdout:
            print(f"     [STDOUT] {process.stdout.strip()}")
        if process.stderr:
            print(f"     [STDERR] {process.stderr.strip()}")
        return process
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"   [失敗的 STDOUT]:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"   [失敗的 STDERR]:\n{e.stderr}", file=sys.stderr)
        raise

def setup_environment():
    """準備虛擬環境並安裝依賴。"""
    print_header("階段 1: 環境準備")

    if VENV_DIR.exists():
        print(f"ℹ️  發現現有虛擬環境 '{VENV_DIR}'，將其移除以確保純淨環境。")
        shutil.rmtree(VENV_DIR)

    print(f"正在建立新的虛擬環境於 '{VENV_DIR}'...")
    run_command([sys.executable, "-m", "venv", str(VENV_DIR)])
    print("✅ 虛擬環境建立成功。")

    if not REQUIREMENTS_FILE.exists():
        print(f"⚠️  警告: 找不到依賴檔案 '{REQUIREMENTS_FILE}'，將無法安裝依賴。")
        raise FileNotFoundError(f"依賴檔案不存在: {REQUIREMENTS_FILE}")

    print(f"正在從 '{REQUIREMENTS_FILE}' 安裝依賴...")
    # 注意：這裡我們安裝 dev.txt，它應該包含運行伺服器所需的一切
    run_command([
        str(VENV_PYTHON),
        "-m", "pip", "install",
        "-r", str(REQUIREMENTS_FILE)
    ])
    print("✅ 依賴安裝完成。")

# --- 看門狗與伺服器監控 ---
server_process = None
watchdog_timer = None

def handle_timeout():
    """看門狗超時處理函式。"""
    global server_process
    print(f"🔥🔥🔥 看門狗觸發！在 {WATCHDOG_TIMEOUT} 秒內未收到任何日誌輸出。🔥🔥🔥", file=sys.stderr)
    print("      伺服器可能已卡死或啟動失敗，正在強制終止...", file=sys.stderr)
    if server_process and server_process.poll() is None:
        server_process.kill()
    sys.exit(1) # 以非零狀態碼退出，標示錯誤

def reset_watchdog():
    """重置看門狗計時器。"""
    global watchdog_timer
    if watchdog_timer:
        watchdog_timer.cancel()
    watchdog_timer = threading.Timer(WATCHDOG_TIMEOUT, handle_timeout)
    watchdog_timer.start()

def start_and_monitor_server():
    """啟動後端伺服器並使用看門狗進行監控。"""
    global server_process
    print_header("階段 2: 啟動後端服務並啟動看門狗監控")

    # 根據目前的專案結構，直接使用 uvicorn 啟動
    command = [
        str(VENV_PYTHON),
        "-m", "uvicorn",
        "src.phoenix_core.main:app",
        "--host", "127.0.0.1",
        "--port", "8088",
        "--log-level", "info",
    ]
    print(f"   🔹 使用 Popen 啟動命令: {' '.join(command)}")

    server_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # 將 stderr 合併到 stdout
        text=True,
        encoding='utf-8',
        bufsize=1  # 行緩衝
    )

    print(f"✅ 伺服器程序已啟動 (PID: {server_process.pid})。")
    print(f"⏳ 正在監控日誌輸出... (看門狗超時: {WATCHDOG_TIMEOUT} 秒)")

    reset_watchdog() # 啟動第一個看門狗計時器

    try:
        for line in iter(server_process.stdout.readline, ''):
            if not line:
                break

            line = line.strip()
            print(f"   [API Server] {line}")
            reset_watchdog() # 每收到一行日誌，就重置看門狗

            # Uvicorn 啟動完成的標準訊息
            if "Application startup complete" in line:
                print("\n✅ 偵測到『應用程式啟動完成』訊息！伺服器已準備就緒。")
                print("   讓伺服器在背景繼續運行 5 秒作為觀察期...")
                time.sleep(5)
                return # 成功啟動，正常返回

        # 如果日誌流結束但未檢測到成功訊息
        print("⚠️  警告: 伺服器日誌流已結束，但未偵測到成功啟動訊息。", file=sys.stderr)

    finally:
        if watchdog_timer:
            watchdog_timer.cancel()

def main():
    """主執行函式，協調所有步驟。"""
    global server_process
    print_header("啟動後端健康檢查腳本")

    try:
        # --- 步驟 1: 環境準備 ---
        setup_environment()

        # --- 步驟 2: 啟動後端服務與看門狗 ---
        start_and_monitor_server()

        # --- 步驟 3: 清理 ---
        print_header("階段 3: 任務完成，執行清理")
        print("✅ 偵錯執行器流程成功結束。")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n❌ 偵錯流程執行失敗: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 無論成功或失敗，都確保清理所有資源
        if server_process and server_process.poll() is None:
            print("   正在終止後端伺服器...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("   ✅ 後端伺服器已成功終止。")
            except subprocess.TimeoutExpired:
                print("   ⚠️ 終止超時，強制抹除。")
                server_process.kill()

if __name__ == "__main__":
    main()
