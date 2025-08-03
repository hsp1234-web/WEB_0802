# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 Colab Debug Runner (V1.0)                                    ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 在本地環境中，以可偵錯、可重現的方式，完整模擬           ║
# ║           Colab 啟動腳本的核心流程。包含環境準備、服務啟動、       ║
# ║           以及看門狗監控機制。                                     ║
# ║   - 架構: 協調器 (本腳本) + 輕量啟動器 (start_api_service.py)      ║
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
            cwd=str(cwd), # 確保 cwd 是字串
            check=check
        )
        # 即使成功，也打印標準輸出和錯誤，便於追蹤
        if process.stdout:
            print(f"     [STDOUT] {process.stdout.strip()}")
        if process.stderr:
            # 將警告等資訊打印到標準輸出，使其與主要日誌流保持一致
            print(f"     [STDERR] {process.stderr.strip()}")
        return process
    except subprocess.CalledProcessError as e:
        # 在錯誤發生時，打印詳細的輸出以便偵錯
        print(f"❌ 命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"   [失敗的 STDOUT]:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"   [失敗的 STDERR]:\n{e.stderr}", file=sys.stderr)
        raise  # 重新引發異常，讓主函式捕獲

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
        print(f"⚠️  警告: 找不到依賴檔案 '{REQUIREMENTS_FILE}'，跳過安裝步驟。")
        return

    print(f"正在從 '{REQUIREMENTS_FILE}' 安裝依賴...")
    run_command([
        str(VENV_PYTHON),
        "-m", "pip", "install",
        "-r", str(REQUIREMENTS_FILE)
    ])
    print("✅ 依賴安裝完成。")

# --- 全域設定 (續) ---
API_SERVICE_SCRIPT = Path("./scripts/start_api_service.py")
WATCHDOG_TIMEOUT = 20.0  # 秒

# --- 看門狗與伺服器監控 ---
server_process = None
watchdog_timer = None

def handle_timeout():
    """看門狗超時處理函式。"""
    global server_process
    print(f"🔥🔥🔥 看門狗觸發！在 {WATCHDOG_TIMEOUT} 秒內未收到任何日誌輸出。🔥🔥🔥", file=sys.stderr)
    print("      伺服器可能已卡死，正在強制終止...", file=sys.stderr)
    if server_process and server_process.poll() is None:
        server_process.kill()
    # 以非零狀態碼退出，標示錯誤
    sys.exit(1)

def reset_watchdog():
    """重置看門狗計時器。"""
    global watchdog_timer
    if watchdog_timer:
        watchdog_timer.cancel()
    watchdog_timer = threading.Timer(WATCHDOG_TIMEOUT, handle_timeout)
    watchdog_timer.start()

import json

def create_debug_config():
    """建立一個用於偵錯的 config.json 檔案。"""
    config_path = Path("./config.json.debug")
    print(f"   🔹 正在建立偵錯設定檔: {config_path}")
    config_data = {
        "system_settings": {"timezone": "Asia/Taipei"},
        "log_settings": {
            "levels": {
                "BATTLE": True, "SUCCESS": True, "INFO": True, "CMD": True,
                "SHELL": True, "ERROR": True, "CRITICAL": True, "PERF": True
            }
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    print(f"   ✅ 偵錯設定檔已建立。")
    return config_path

def start_and_monitor_server(config_path: Path):
    """啟動後端伺服器並使用看門狗進行監控。"""
    global server_process
    print_header("階段 2: 啟動後端服務並啟動看門狗監控")

    if not API_SERVICE_SCRIPT.exists():
        raise FileNotFoundError(f"找不到後端啟動腳本: {API_SERVICE_SCRIPT}")

    command = [str(VENV_PYTHON), str(API_SERVICE_SCRIPT), "--config", str(config_path)]
    print(f"   🔹 使用 Popen 啟動命令: {' '.join(command)}")

    # 使用 Popen 在背景啟動伺服器
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
        # 逐行讀取伺服器日誌
        for line in iter(server_process.stdout.readline, ''):
            if not line: # 如果輸出結束，跳出迴圈
                break

            line = line.strip()
            print(f"   [API Server] {line}")
            reset_watchdog() # 每收到一行日誌，就重置看門狗

            # 檢查是否啟動成功
            if "Application startup complete" in line:
                print("\n✅ 偵測到『應用程式啟動完成』訊息！伺服器已準備就緒。")
                print("   讓伺服器在背景繼續運行 10 秒作為測試觀察期...")
                time.sleep(10)
                return # 成功啟動，正常返回

        # 如果日誌流結束但未檢測到成功訊息
        print("⚠️  警告: 伺服器日誌流已結束，但未偵測到成功啟動訊息。", file=sys.stderr)

    finally:
        # 無論如何，確保計時器被取消
        if watchdog_timer:
            watchdog_timer.cancel()

def main():
    """主執行函式，協調所有步驟。"""
    global server_process
    config_path = None
    print_header("啟動 Colab 本地偵錯執行器")

    try:
        # --- 步驟 1: 環境準備 ---
        setup_environment()
        config_path = create_debug_config()

        # --- 步驟 2: 啟動後端服務與看門狗 ---
        start_and_monitor_server(config_path)

        # --- 步驟 3: 等待與清理 ---
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

        if config_path and config_path.exists():
            print(f"   正在清理偵錯設定檔 {config_path}...")
            config_path.unlink()
            print("   ✅ 設定檔已清理。")


if __name__ == "__main__":
    main()
