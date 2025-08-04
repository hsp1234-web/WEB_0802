# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 鳳凰之心 - V38 Colab 指揮中心 (VENV Fix)           ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - V38 更新日誌:                                                      ║
# ║   - **修正 VENV 問題**: 強制為子進程設定 VIRTUAL_ENV 環境變數。      ║
# ║   - 這確保了 uv 和 uvicorn 都會在我們創建的虛擬環境中正確運作。      ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 💎 鳳凰之心指揮中心 V38 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 程式碼與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "0.5.1" #@param {type:"string"}
#@markdown **專案資料夾名稱 (PROJECT_FOLDER_NAME)**
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown **強制刷新後端程式碼 (FORCE_REPO_REFRESH)**
FORCE_REPO_REFRESH = True #@param {type:"boolean"}

#@markdown ---
#@markdown ### Part 2: 應用程式參數
#@markdown > **設定指揮中心的核心運行參數。**
#@markdown ---
#@markdown **儀表板更新頻率 (秒) (REFRESH_RATE_SECONDS)**
REFRESH_RATE_SECONDS = 1.5 #@param {type:"number"}
#@markdown **後端 API 服務埠號 (API_PORT)**
API_PORT = 8088 #@param {type:"integer"}
#@markdown **日誌顯示行數 (LOG_DISPLAY_LINES)**
LOG_DISPLAY_LINES = 50 #@param {type:"integer"}

#@markdown ---
#@markdown ### Part 3: 日誌顯示設定
#@markdown > **選擇您想在儀表板上看到的日誌等級。**
#@markdown ---
#@markdown **顯示戰鬥日誌 (SHOW_LOG_LEVEL_BATTLE)**
SHOW_LOG_LEVEL_BATTLE = True #@param {type:"boolean"}
#@markdown **顯示成功日誌 (SHOW_LOG_LEVEL_SUCCESS)**
SHOW_LOG_LEVEL_SUCCESS = True #@param {type:"boolean"}
#@markdown **顯示資訊日誌 (SHOW_LOG_LEVEL_INFO)**
SHOW_LOG_LEVEL_INFO = False #@param {type:"boolean"}
#@markdown **顯示命令日誌 (SHOW_LOG_LEVEL_CMD)**
SHOW_LOG_LEVEL_CMD = False #@param {type:"boolean"}
#@markdown **顯示系統日誌 (SHOW_LOG_LEVEL_LOG_SHELL)**
SHOW_LOG_LEVEL_LOG_SHELL = False #@param {type:"boolean"}
#@markdown **顯示錯誤日誌 (SHOW_LOG_LEVEL_ERROR)**
SHOW_LOG_LEVEL_ERROR = True #@param {type:"boolean"}
#@markdown **顯示嚴重錯誤日誌 (SHOW_LOG_LEVEL_CRITICAL)**
SHOW_LOG_LEVEL_CRITICAL = True #@param {type:"boolean"}
#@markdown **顯示效能日誌 (SHOW_LOG_LEVEL_PERF)**
SHOW_LOG_LEVEL_PERF = False #@param {type:"boolean"}


# ==============================================================================
# 🚀 核心邏輯 (測試模式)
# ==============================================================================
import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import json
import threading
from collections import deque
from datetime import datetime

# ==============================================================================
# 🛡️ 看門狗監控邏輯
# ==============================================================================
server_process = None
watchdog_timer = None

def handle_timeout():
    """處理超時事件。"""
    global server_process
    log_message("❌ 看門狗觸發！後端服務在 15 秒內無任何日誌輸出，可能已掛起。")
    log_message("🔥 正在終止服務程序...")
    if server_process and server_process.poll() is None:
        server_process.kill()
        log_message("✅ 服務程序已被看門狗終止。")

def reset_watchdog(timeout=15.0):
    """重置看門狗計時器。"""
    global watchdog_timer
    if watchdog_timer:
        watchdog_timer.cancel()
    watchdog_timer = threading.Timer(timeout, handle_timeout)
    watchdog_timer.start()

# ==============================================================================
# 核心邏輯
# ==============================================================================
logs_deque = deque(maxlen=LOG_DISPLAY_LINES)

def log_message(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    logs_deque.append(log_entry)
    print(log_entry, file=sys.stderr)

def setup_environment():
    """
    在主執行緒中執行所有環境設定、下載和安裝步驟。
    成功時返回 (project_path, venv_python) tuple，失敗時返回 (None, None)。
    """
    try:
        log_message("準備專案環境 (使用策略 B)...")
        execution_root = Path.cwd()
        project_path = execution_root / PROJECT_FOLDER_NAME

        if FORCE_REPO_REFRESH and project_path.exists():
            log_message(f"偵測到強制刷新，正在刪除舊的專案資料夾: {project_path}")
            shutil.rmtree(project_path)
            log_message("✅ 舊資料夾已刪除。")

        if not project_path.exists():
            log_message(f"正在從 Github 下載程式碼 (分支: {TARGET_BRANCH_OR_TAG})...")
            subprocess.run(
                ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)],
                check=True, capture_output=True
            )
            log_message(f"✅ 程式碼下載成功於 {project_path}。")
        else:
            log_message(f"專案資料夾 {project_path} 已存在，跳過下載。")

        venv_path = project_path / ".venv"
        if not venv_path.exists():
            log_message(f"正在使用 'uv venv' 建立虛擬環境於 {venv_path}...")
            subprocess.run(["uv", "venv", str(venv_path)], check=True, capture_output=True)
            log_message("✅ 虛擬環境建立成功。")
        else:
            log_message("虛擬環境已存在。")

        if sys.platform == "win32":
            venv_python = venv_path / "Scripts" / "python.exe"
        else:
            venv_python = venv_path / "bin" / "python"

        core_requirements_path = project_path / "requirements" / "requirements-core.txt"

        log_message("為確保安裝純淨，正在清理 uv 快取...")
        subprocess.run(["uv", "cache", "clean"], check=True, capture_output=True)
        log_message("✅ uv 快取清理完成。")

        log_message(f"正在從 {core_requirements_path} 安裝核心依賴...")
        # 這是我們預期要使用的正確安裝指令
        # 最後的偵錯手段：直接在指令中傳遞所有套件，繞過 requirements.txt
        requirements_content = [
            "aiohttp==3.12.15",
            "fastapi==0.116.1",
            "psutil==7.0.0",
            "pydantic-settings==2.10.1",
            "uvicorn[standard]==0.35.0",
            "websockets==12.0",
            "pytz==2025.2",
            "uv==0.1.33"
        ]
        uv_install_command = ["uv", "pip", "install"] + requirements_content + ["--python", str(venv_python)]

        process = subprocess.run(uv_install_command, capture_output=True, text=True, check=True)
        log_message(f"✅ 核心依賴安裝完成。 (uv-pip stdout: {len(process.stdout)} bytes)")
        if len(process.stdout) == 0:
             log_message("⚠️ 警告: 安裝過程沒有任何輸出，這可能表示安裝未成功。")

        return project_path, venv_python

    except subprocess.CalledProcessError as e:
        stdout = e.stdout.decode(errors='ignore') if isinstance(e.stdout, bytes) else e.stdout
        stderr = e.stderr.decode(errors='ignore') if isinstance(e.stderr, bytes) else e.stderr
        log_message(f"❌ 環境設定期間發生子程序錯誤！")
        log_message(f"   - 命令: {' '.join(e.cmd)}")
        log_message(f"   - STDOUT: {stdout}")
        log_message(f"   - STDERR: {stderr}")
        return None, None
    except Exception as e:
        log_message(f"❌ 環境設定期間發生致命錯誤: {e}")
        return None, None

def monitor_server(project_path, venv_python):
    """
    在背景執行緒中啟動並監控伺服器。
    """
    global server_process
    try:
        log_message("正在生成後端設定檔...")
        config_data = {"log_settings": {
            "BATTLE": SHOW_LOG_LEVEL_BATTLE, "SUCCESS": SHOW_LOG_LEVEL_SUCCESS,
            "INFO": SHOW_LOG_LEVEL_INFO, "CMD": SHOW_LOG_LEVEL_CMD,
            "LOG_SHELL": SHOW_LOG_LEVEL_LOG_SHELL, "ERROR": SHOW_LOG_LEVEL_ERROR,
            "CRITICAL": SHOW_LOG_LEVEL_CRITICAL, "PERF": SHOW_LOG_LEVEL_PERF
        }}
        config_file_path = project_path / "temp_config_for_runner.json"
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        log_message(f"✅ 後端設定檔已生成於 {config_file_path}。")

        process_env = os.environ.copy()
        process_env["PHOENIX_CONFIG_PATH"] = str(config_file_path)
        process_env["VIRTUAL_ENV"] = str(venv_python.parent.parent)
        process_env["PATH"] = f"{venv_python.parent}:{process_env.get('PATH', '')}"

        log_message(f"🔥 正在啟動並監控後端核心服務於埠 {API_PORT}...")
        log_file_path = project_path / "api_server.log"

        uvicorn_command = [str(venv_python), "-m", "uvicorn", "src.phoenix_core.main:app", "--host", "0.0.0.0", "--port", str(API_PORT)]

        server_process = subprocess.Popen(
            uvicorn_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1,
            cwd=str(project_path),
            env=process_env
        )

        log_message("✅ 後端核心服務已啟動。看門狗已部署。")
        reset_watchdog()

        with open(log_file_path, "w", encoding="utf-8") as log_file:
            for line in iter(server_process.stdout.readline, ''):
                if not line: break
                clean_line = line.strip()
                log_message(f"[服務日誌] {clean_line}")
                log_file.write(line)
                log_file.flush()
                reset_watchdog()

        if watchdog_timer:
            watchdog_timer.cancel()

        return_code = server_process.wait()
        log_message(f"✅ 後端服務程序已終止，返回碼: {return_code}。")

    except Exception as e:
        log_message(f"❌ 伺服器監控執行緒發生致命錯誤: {e}")

def main():
    print("--- main() 函數開始 ---", file=sys.stderr)

    # 步驟 1: 在主執行緒中設定環境
    project_path, venv_python = setup_environment()

    if project_path and venv_python:
        # 步驟 2: 在背景執行緒中啟動和監控伺服器
        monitor_thread = threading.Thread(target=monitor_server, args=(project_path, venv_python))
        monitor_thread.start()
        print("--- 伺服器監控執行緒已啟動 ---", file=sys.stderr)
        monitor_thread.join()
        print("--- 伺服器監控執行緒已結束 ---", file=sys.stderr)
    else:
        log_message("❌ 環境設定失敗，無法啟動伺服器。")

    print("--- main() 函數結束 ---", file=sys.stderr)

if __name__ == "__main__":
    main()
