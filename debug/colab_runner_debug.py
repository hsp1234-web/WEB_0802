# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 鳳凰之心 - Colab 執行器除錯腳本 (安全模式) v0.1          ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║  **設計目標:**                                                       ║
# ║  1. **安全至上**: 在完全隔離的環境中執行，避免影響主系統。         ║
# ║  2. **看門狗監控**: 自動偵測並終止無回應的子進程，防止系統崩潰。   ║
# ║  3. **日誌詳盡**: 捕捉所有輸出，便於分析問題根源。                 ║
# ║  4. **繁體中文**: 所有註解與輸出均為繁體中文。                     ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import json
from datetime import datetime
import threading

# --- 組態設定 ---

# 將日誌檔案直接放在 'debug' 資料夾下，避免 __file__ 在某些環境中不存在的問題
LOG_FILE_PATH = Path("debug/colab_runner_debug.log")

# 隔離執行環境的根目錄
SANDBOX_DIR = Path("debug/run_sandbox")

# 後端程式碼設定
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git"
TARGET_BRANCH_OR_TAG = "0.6.4"  # 根據使用者要求設定
PROJECT_FOLDER_NAME = "WEB1"
FORCE_REPO_REFRESH = True

# 應用程式參數
API_PORT = 8088

# 看門狗逾時時間 (秒)
WATCHDOG_TIMEOUT = 30.0

# --- 全域變數 ---
watchdog_timer = None
server_process = None

# --- 核心功能函式 ---

def setup_logging():
    """設定日誌系統，清除舊的日誌檔案。"""
    if LOG_FILE_PATH.exists():
        os.remove(LOG_FILE_PATH)
    LOG_FILE_PATH.parent.mkdir(exist_ok=True)
    log_message("日誌系統已初始化。")

def log_message(message, level="INFO"):
    """將帶有時間戳的訊息寫入日誌檔案並打印到控制台。"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 針對遠端日誌，我們保持原樣，不加時間戳，以便閱讀
    if level == "REMOTE":
        log_entry = message
    else:
        log_entry = f"[{timestamp}] [{level}] {message}"

    print(log_entry, flush=True)
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def handle_timeout():
    """看門狗超時處理函式。"""
    global server_process
    if server_process and server_process.poll() is None:
        log_message("🔥 看門狗觸發！子進程無回應，正在強制終止...", level="CRITICAL")
        server_process.kill()
        log_message("子進程已被終止。", level="CRITICAL")
    else:
        log_message("看門狗觸發，但子進程似乎已結束。", level="WARNING")

def reset_watchdog(timeout=WATCHDOG_TIMEOUT):
    """重置看門狗計時器。"""
    global watchdog_timer
    if watchdog_timer:
        watchdog_timer.cancel()
    watchdog_timer = threading.Timer(timeout, handle_timeout)
    watchdog_timer.start()

def setup_environment():
    """
    執行所有耗時的一次性環境準備工作。
    此函式會在一個隔離的沙箱目錄中執行，直到所有步驟完成或發生錯誤。
    返回準備好的路徑資訊供後續步驟使用。
    """
    try:
        log_message("▶️ [階段 1/3] 準備專案環境...")

        # --- 1. 清理並建立沙箱 ---
        if SANDBOX_DIR.exists():
            log_message(f"🗑️ 正在清理舊的沙箱目錄: {SANDBOX_DIR}")
            shutil.rmtree(SANDBOX_DIR)
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        log_message(f"✅ 沙箱目錄已建立於: {SANDBOX_DIR.resolve()}")

        project_path = SANDBOX_DIR / PROJECT_FOLDER_NAME

        # --- 2. 下載程式碼 ---
        if not project_path.exists():
            log_message(f"⏳ 正在從 Github 下載程式碼 (分支: {TARGET_BRANCH_OR_TAG})...")
            git_command = ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)]
            result = subprocess.run(git_command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                log_message(f"❌ Git clone 失敗。返回碼: {result.returncode}", level="ERROR")
                log_message(f"--- STDERR ---\n{result.stderr}\n------------", level="ERROR")
                return None
            log_message("✅ 程式碼下載成功。")
        else:
            # 在沙箱模式下，這段程式碼理論上不會執行，因為我們每次都清理沙箱
            log_message("✅ 專案資料夾已存在，跳過下載。")

        # --- 3. 建立虛擬環境 ---
        venv_path = project_path / ".venv"
        if not venv_path.exists():
            log_message(f"⏳ 正在使用 'uv venv' 建立虛擬環境...")
            result = subprocess.run(["uv", "venv", str(venv_path)], check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                log_message(f"❌ 建立虛擬環境失敗。返回碼: {result.returncode}", level="ERROR")
                log_message(f"--- STDERR ---\n{result.stderr}\n------------", level="ERROR")
                return None
            log_message("✅ 虛擬環境建立成功。")
        else:
            log_message("✅ 虛擬環境已存在，跳過建立。")

        # --- 4. 安裝依賴 ---
        venv_python = (venv_path / "bin" / "python").resolve()
        log_message("⏳ 正在使用 'uv pip sync' 安裝核心依賴...")
        core_requirements_path = project_path / "requirements/requirements-core.txt"
        if not core_requirements_path.exists():
            log_message(f"❌ 找不到依賴檔案: {core_requirements_path}", level="ERROR")
            return None

        # 建立一個啟用了虛擬環境的子進程環境
        install_env = os.environ.copy()
        install_env["VIRTUAL_ENV"] = str(venv_path)
        install_env["PATH"] = f"{venv_path / 'bin'}:{install_env.get('PATH', '')}"

        # 在啟用了 venv 的情況下，不再需要 --python 參數
        uv_install_command = ["uv", "pip", "sync", str(core_requirements_path)]

        result = subprocess.run(
            uv_install_command,
            check=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=install_env # 使用為安裝客製化的環境變數
        )

        if result.returncode != 0:
            log_message(f"❌ 安裝依賴失敗。返回碼: {result.returncode}", level="ERROR")
            log_message(f"--- STDERR ---\n{result.stderr}\n------------", level="ERROR")
            return None
        log_message("✅ 核心依賴安裝完成。")

        log_message("✅ [階段 1/3] 環境準備成功。")
        return {"project_path": project_path, "venv_python": venv_python}

    except Exception as e:
        log_message(f"❌ 在環境準備階段發生致命錯誤: {e}", level="ERROR")
        return None

def main():
    """腳本主執行函式。"""
    setup_logging()
    log_message("🚀 除錯腳本啟動。")
    log_message(f"日誌檔案位於: {LOG_FILE_PATH.resolve()}")

    env_paths = setup_environment()

    if env_paths:
        log_message("▶️ [階段 2/3] 啟動受監控的後端服務...")

        project_path = env_paths["project_path"]
        venv_python = env_paths["venv_python"]

        process_env = os.environ.copy()
        process_env["VIRTUAL_ENV"] = str(venv_python.parent.parent)
        process_env["PATH"] = f"{venv_python.parent}:{process_env.get('PATH', '')}"
        # 強制子進程進行無緩衝輸出，確保日誌即時性
        process_env["PYTHONUNBUFFERED"] = "1"

        uvicorn_command = [
            str(venv_python), "-m", "uvicorn",
            "src.phoenix_core.main:app",
            "--host", "0.0.0.0",
            "--port", str(API_PORT)
        ]

        log_message(f"執行指令: {' '.join(uvicorn_command)}")

        global server_process
        try:
            # 使用 Popen 啟動非阻塞子進程
            server_process = subprocess.Popen(
                uvicorn_command,
                cwd=str(project_path),
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # 將 stderr 合併到 stdout
                text=True,
                encoding='utf-8',
                errors='replace' # 如果有無法解碼的字元，替換它
            )

            log_message(f"✅ 子進程已啟動 (PID: {server_process.pid})。開始監控輸出...")
            reset_watchdog() # 啟動看門狗

            # 讀取子進程輸出並重置看門狗
            for line in iter(server_process.stdout.readline, ''):
                if line:
                    # 使用 REMOTE 等級來直接打印子進程的原始輸出
                    log_message(f"[Uvicorn] {line.strip()}", level="REMOTE")
                    reset_watchdog()

            # 等待進程結束並取得返回碼
            return_code = server_process.wait()
            log_message(f"子進程已正常結束，返回碼: {return_code}。")

        except Exception as e:
            log_message(f"❌ 執行或監控子進程時發生錯誤: {e}", level="ERROR")

        finally:
            if watchdog_timer:
                watchdog_timer.cancel() # 清理計時器

            # 確保進程已被終結
            if server_process and server_process.poll() is None:
                log_message("腳本結束，但子進程仍在運行。正在終止...", level="WARNING")
                server_process.kill()

            log_message("⏹️ [階段 2/3] 監控結束。")

    else:
        log_message("❌ 由於環境準備失敗，啟動流程已中止。", level="ERROR")

    log_message("🏁 除錯腳本執行完畢。")


if __name__ == "__main__":
    main()
