# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║                  🚀 鳳凰之心 - 監控面板 V32 (整合版)                   ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 說明: 此腳本為 Colab 中的主要進入點，用於啟動後端並顯示即時監控   ║
# ║         儀表板。                                                     ║
# ║ - 依賴: `db_queries.py`, `watchdog.py`, `psutil`                     ║
# ║ - 版本: 0.5.0 (整合動態資源監控)                                   ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# --- Colab 使用者介面參數 ---
#@title 🚀 V32 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### Part 1: 程式碼與環境設定
#@markdown > 設定 Git 倉庫、分支或標籤，以及專案資料夾。
#@markdown ---
#@markdown 後端程式碼倉庫 (REPOSITORY_URL)
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown 後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)
TARGET_BRANCH_OR_TAG = "0.4.6" #@param {type:"string"}
#@markdown 專案資料夾名稱 (PROJECT_FOLDER_NAME)
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown 強制刷新後端程式碼 (FORCE_REPO_REFRESH)
FORCE_REPO_REFRESH = True #@param {type:"boolean"}

#@markdown ---
#@markdown ### Part 2: 應用程式參數
#@markdown > 設定指揮中心的核心運行參數。
#@markdown ---
#@markdown 儀表板更新頻率 (秒) (REFRESH_RATE_SECONDS)
REFRESH_RATE_SECONDS = 1.0 #@param {type:"number"}
#@markdown 時區設定 (TIMEZONE)
TIMEZONE = "Asia/Taipei" #@param {type:"string"}
#@markdown 後端 API 服務埠號 (API_PORT)
API_PORT = 8088 #@param {type:"integer"}

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
#@markdown **顯示系統日誌 (SHOW_LOG_LEVEL_SHELL)**
SHOW_LOG_LEVEL_SHELL = False #@param {type:"boolean"}
#@markdown **顯示錯誤日誌 (SHOW_LOG_LEVEL_ERROR)**
SHOW_LOG_LEVEL_ERROR = True #@param {type:"boolean"}
#@markdown **顯示嚴重錯誤日誌 (SHOW_LOG_LEVEL_CRITICAL)**
SHOW_LOG_LEVEL_CRITICAL = True #@param {type:"boolean"}
#@markdown **顯示效能日誌 (SHOW_LOG_LEVEL_PERF)**
SHOW_LOG_LEVEL_PERF = False #@param {type:"boolean"}
#@markdown 日誌顯示行數 (LOG_DISPLAY_LINES)
LOG_DISPLAY_LINES = 50 #@param {type:"integer"}

import os
import sys
import time
import sqlite3
import subprocess
import shutil
from datetime import datetime
from IPython.display import display, clear_output
import psutil # 用於獲取系統資源使用率

# --- 階段一：環境準備 ---
def prepare_environment():
    """
    準備執行環境，包括下載程式碼、切換目錄和設定 Python 路徑。
    這是解決 Colab 中 ModuleNotFoundError 的根本方法。
    """
    # 在 Colab 中，內容通常位於 /content
    base_path = "/content"
    project_path = os.path.join(base_path, PROJECT_FOLDER_NAME)

    print(f"📁 專案目錄設定為: {project_path}")

    if FORCE_REPO_REFRESH and os.path.exists(project_path):
        print(f"🔄 偵測到強制刷新，正在刪除舊目錄...")
        shutil.rmtree(project_path)

    if not os.path.exists(project_path):
        print(f"克隆儲存庫從 {REPOSITORY_URL} 到 {project_path}...")
        subprocess.run([
            "git", "clone", "--depth", "1", "--branch", TARGET_BRANCH_OR_TAG,
            REPOSITORY_URL, project_path
        ], check=True)
    else:
        print("✅ 專案目錄已存在，跳過下載。")

    # 關鍵步驟：切換當前工作目錄到專案根目錄
    os.chdir(project_path)
    print(f"pwd: {os.getcwd()}")


    # 關鍵步驟：將當前目錄（即專案根目錄）加入到 sys.path
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    print("✅ 環境準備完成，Python 路徑已設定。")

# --- 執行環境準備 ---
prepare_environment()

# --- 現在可以安全地導入專案模組了 ---
from src.phoenix_core.db_queries import query_logs_by_level
from src.phoenix_core.watchdog import check_heartbeat_status


# --- 階段二：後端啟動 ---
def setup_backend():
    """
    安裝依賴並在背景啟動後端 Uvicorn 伺服器。
    """
    print("🚀 正在準備後端環境...")

    # 1. 安裝依賴
    requirements_path = "requirements/base.txt"
    print(f"--- 正在從 {requirements_path} 安裝依賴... ---")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_path], check=True)
        print("✅ 依賴安裝完成。")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依賴安裝失敗: {e}")
        return False

    # 2. 啟動後端服務
    print(f"🔥 正在啟動後端服務於埠 {API_PORT}...")
    # 使用 Popen 在背景執行，並將日誌導出到檔案以便排錯
    log_file = open("api_server.log", "w")
    subprocess.Popen([
        sys.executable, "-m", "uvicorn", "src.phoenix_core.main:app",
        "--host", "0.0.0.0", "--port", str(API_PORT)
    ], stdout=log_file, stderr=log_file)

    print("✅ 後端服務已在背景啟動。")

    # 3. 等待資料庫檔案生成
    print("--- 等待 state.db 生成 (最多 10 秒)... ---")
    db_path = "state.db"
    for _ in range(10):
        if os.path.exists(db_path):
            print("✅ state.db 已找到！")
            return True
        time.sleep(1)

    print(f"❌ 錯誤：等待超時，找不到 {db_path}。請檢查 api_server.log 以了解後端啟動詳情。")
    return False

# --- 階段三：UI 顯示邏輯 ---
WIDTH = 90

def print_header(title):
    print('┌' + '─' * (WIDTH - 2) + '┐')
    print(f"│{title.center(WIDTH - 2)}│")
    print('└' + '─' * (WIDTH - 2) + '┘')

def print_box_header(title):
    print('\n┌─ ' + title + ' ' + '─' * (WIDTH - len(title) - 5) + '┐')
    print('│' + ' ' * (WIDTH - 2) + '│')

def print_box_footer():
    print('│' + ' ' * (WIDTH - 2) + '│')
    print('└' + '─' * (WIDTH - 2) + '┘')

def get_selected_log_levels():
    levels = []
    if SHOW_LOG_LEVEL_BATTLE: levels.append('BATTLE')
    if SHOW_LOG_LEVEL_SUCCESS: levels.append('SUCCESS')
    if SHOW_LOG_LEVEL_INFO: levels.append('INFO')
    if SHOW_LOG_LEVEL_CMD: levels.append('CMD')
    if SHOW_LOG_LEVEL_SHELL: levels.append('SHELL')
    if SHOW_LOG_LEVEL_ERROR: levels.append('ERROR')
    if SHOW_LOG_LEVEL_CRITICAL: levels.append('CRITICAL')
    if SHOW_LOG_LEVEL_PERF: levels.append('PERF')
    return levels

def print_log_panel(conn):
    print_box_header("📜 近況彙報")
    levels_to_show = get_selected_log_levels()
    all_logs = []
    for level in levels_to_show:
        logs = query_logs_by_level(conn, level, limit=LOG_DISPLAY_LINES)
        for log in logs:
            dt_obj = datetime.fromisoformat(log[1])
            all_logs.append((dt_obj, log[2], log[4]))
    all_logs.sort(key=lambda x: x[0], reverse=True)
    display_logs = all_logs[:LOG_DISPLAY_LINES]
    for log_time, level, message in display_logs:
        ts = log_time.strftime("%H:%M:%S")
        icon_map = {'SUCCESS': '✅', 'ERROR': '❌', 'BATTLE': '⚔️', 'INFO': '▶️'}
        icon = icon_map.get(level, '🔹')
        log_line = f" [{ts}] [{level}] {icon} {message}"
        print(f"│{log_line:<{WIDTH - 2}}│")
    print_box_footer()

def print_status_panel(conn):
    """顯示即時狀態面板，包含動態的 CPU 和 RAM 資訊。"""
    print_box_header("⚡️ 即時狀態")
    now = datetime.now()
    ts = now.strftime("%H:%M:%S")

    # 動態獲取系統資源
    cpu_percent = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    ram_used_gb = ram.used / (1024**3)
    ram_total_gb = ram.total / (1024**3)

    # 獲取心跳狀態
    heartbeat_status = check_heartbeat_status(conn, 15)
    heartbeat_text = "[💓 心跳正常]" if heartbeat_status == 'OK' else f"[🚨 心跳異常: {heartbeat_status}]"

    # 根據心跳決定主要狀態
    main_status = "[🟢 核心運行中]" if heartbeat_status == 'OK' else "[🔴 核心無回應]"

    status_line = f"  {ts} | CPU: {cpu_percent:5.1f}% | RAM: {ram_used_gb:.1f}/{ram_total_gb:.1f} GB | {main_status} {heartbeat_text}"
    print(f"│{status_line:<{WIDTH - 2}}│")
    print_box_footer()

def print_action_panel():
    print_box_header("🔗 行動指令")
    line1 = "  所有任務已執行完畢！點擊下方連結以開啟互動式操作儀表板。"
    line2 = f"  👉 http://localhost:{API_PORT}/"
    print(f"│{line1:<{WIDTH - 2}}│")
    print('│' + ' ' * (WIDTH - 2) + '│')
    print(f"│{line2:<{WIDTH - 2}}│")
    print_box_footer()

# --- 階段四：主執行迴圈 ---
def main_loop():
    DB_PATH = "state.db" # 現在我們在專案根目錄，可以直接使用相對路徑
    if not os.path.exists(DB_PATH):
        print(f"❌ 錯誤：找不到資料庫檔案 '{DB_PATH}'。後端服務是否已正確啟動並生成了資料庫？")
        return
    conn = None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        while True:
            clear_output(wait=True)
            print_header("🚀 鳳凰之心 - 監控面板 🚀")
            print_log_panel(conn)
            print_status_panel(conn)
            print_action_panel()
            time.sleep(REFRESH_RATE_SECONDS)
    except sqlite3.Error as e:
        print(f"❌ 資料庫錯誤: {e}")
    except KeyboardInterrupt:
        print("\n🛑 使用者手動中斷。")
    finally:
        if conn:
            conn.close()

# --- 主程式入口 ---
if __name__ == "__main__":
    # 1. 執行環境設定
    setup_backend()
    # 2. 進入主迴圈
    main_loop()
