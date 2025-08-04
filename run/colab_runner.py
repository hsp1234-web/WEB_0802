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

logs_deque = deque(maxlen=LOG_DISPLAY_LINES)

def log_message(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    logs_deque.append(log_entry)
    print(log_entry, file=sys.stderr)

def background_worker():
    try:
        log_message("準備專案環境...")
        base_path = Path(".")
        project_path = base_path / PROJECT_FOLDER_NAME

        if FORCE_REPO_REFRESH and project_path.exists():
            log_message("偵測到強制刷新，正在刪除舊的專案資料夾...")
            shutil.rmtree(project_path)
            log_message("✅ 舊資料夾已刪除。")

        if not project_path.exists():
            log_message(f"正在從 Github 下載程式碼 (分支: {TARGET_BRANCH_OR_TAG})...")
            git_command = ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)]
            subprocess.run(git_command, check=True)
            log_message("✅ 程式碼下載成功。")
        else:
            log_message("專案資料夾已存在，跳過下載。")

        os.chdir(project_path)
        log_message(f"工作目錄已變更至: {os.getcwd()}")
        if str(project_path) not in sys.path:
            sys.path.insert(0, str(project_path))

        # --- 步驟 1.5: 建立並準備虛擬環境 ---
        venv_path = Path(".venv").resolve()
        if not venv_path.exists():
            log_message(f"正在建立虛擬環境於 {venv_path}...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            log_message("✅ 虛擬環境建立成功。")
        else:
            log_message("虛擬環境已存在。")

        # 定義 venv 中的 python 解譯器路徑
        venv_python = (venv_path / "bin" / "python").resolve()

        # 建立一個包含 VIRTUAL_ENV 的環境變數副本
        process_env = os.environ.copy()
        process_env["VIRTUAL_ENV"] = str(venv_path)
        # 確保 venv 的 bin 目錄在 PATH 的最前面
        process_env["PATH"] = f"{venv_path / 'bin'}:{process_env.get('PATH', '')}"

        log_message("正在生成後端設定檔...")
        config_data = {"log_settings": {
            "BATTLE": SHOW_LOG_LEVEL_BATTLE, "SUCCESS": SHOW_LOG_LEVEL_SUCCESS,
            "INFO": SHOW_LOG_LEVEL_INFO, "CMD": SHOW_LOG_LEVEL_CMD,
            "LOG_SHELL": SHOW_LOG_LEVEL_LOG_SHELL, "ERROR": SHOW_LOG_LEVEL_ERROR,
            "CRITICAL": SHOW_LOG_LEVEL_CRITICAL, "PERF": SHOW_LOG_LEVEL_PERF
        }}
        config_file_path = Path("temp_config_for_runner.json")
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        log_message("✅ 後端設定檔已生成。")
        process_env["PHOENIX_CONFIG_PATH"] = str(config_file_path.resolve())

        log_message("正在檢查並安裝 uv 加速器...")
        subprocess.run([str(venv_python), "-m", "pip", "install", "-q", "uv"], check=True, env=process_env)
        log_message("✅ uv 安裝完成。")

        log_message("正在使用 uv 安裝核心依賴...")
        core_requirements_path = "requirements/requirements-core.txt"
        uv_install_command = [str(venv_python), "-m", "uv", "pip", "install", "-r", core_requirements_path]

        process = subprocess.run(uv_install_command, capture_output=True, text=True, check=False, env=process_env)
        log_message(f"--- UV Install STDOUT ---\n{process.stdout}\n------------------------")
        if process.stderr:
            log_message(f"--- UV Install STDERR ---\n{process.stderr}\n------------------------")
        if process.returncode != 0:
            raise RuntimeError(f"uv pip install failed: {process.stderr}")

        log_message("✅ 核心依賴安裝完成。")

        log_message(f"🔥 正在啟動後端核心服務於埠 {API_PORT}...")
        log_file = open("api_server.log", "w")
        uvicorn_command = [str(venv_python), "-m", "uvicorn", "src.phoenix_core.main:app", "--host", "0.0.0.0", "--port", str(API_PORT)]
        subprocess.Popen(uvicorn_command, stdout=log_file, stderr=subprocess.STDOUT, cwd=Path.cwd(), env=process_env)
        log_message("✅ 後端核心服務已在背景啟動。")

    except Exception as e:
        log_message(f"❌ 背景任務發生致命錯誤: {e}")

def main():
    print("--- main() 函數開始 ---", file=sys.stderr)
    worker_thread = threading.Thread(target=background_worker)
    worker_thread.start()
    print("--- 背景工作執行緒已啟動 ---", file=sys.stderr)
    worker_thread.join()
    print("--- 背景工作執行緒已結束 ---", file=sys.stderr)
    print("--- main() 函數結束 ---", file=sys.stderr)

if __name__ == "__main__":
    main()
