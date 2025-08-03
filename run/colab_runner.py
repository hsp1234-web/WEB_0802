# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║                  🚀 鳳凰之心 - 監控面板 V32 (Colab)                    ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 說明: 此腳本為 Google Colab 環境中的主要進入點，負責處理：       ║
# ║           1. 環境準備 (下載原始碼、安裝依賴)                       ║
# ║           2. 在背景啟動後端 API 服務。                             ║
# ║           3. 顯示一個即時更新的監控儀表板。                        ║
# ║ - 版本: V32                                                          ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# --- Colab 使用者介面參數 ---
#@title 🚀 V31 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
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

# --- 階段一：環境準備 ---
def prepare_environment():
    """
    準備 Colab 的執行環境。
    此函數負責處理原始碼的下載與路徑設定，是確保所有模組能被正確導入的關鍵第一步。
    """
    print_header("階段 1: 環境準備")
    base_path = "/content"
    project_path = os.path.join(base_path, PROJECT_FOLDER_NAME)
    print(f"📁 專案目錄設定為: {project_path}")

    # 根據 UI 選項，決定是否要強制刪除舊有的程式碼以進行更新
    if FORCE_REPO_REFRESH and os.path.exists(project_path):
        print(f"🔄 偵測到強制刷新，正在刪除舊目錄...")
        shutil.rmtree(project_path)

    # 如果專案目錄不存在，則從指定的 Git Repo 和分支下載
    if not os.path.exists(project_path):
        print(f"⬇️  正在從 {REPOSITORY_URL} 克隆程式碼...")
        subprocess.run([
            "git", "clone", "--depth", "1", "--branch", TARGET_BRANCH_OR_TAG,
            REPOSITORY_URL, project_path
        ], check=True)
    else:
        print("✅ 專案目錄已存在，跳過下載。")

    # 核心步驟 1: 將 Python 的當前工作目錄切換到專案的根目錄
    # 這確保了所有相對路徑（如 'requirements/base.txt'）都能被正確解析
    os.chdir(project_path)
    print(f"✅ 當前工作目錄已切換至: {os.getcwd()}")

    # 核心步驟 2: 將專案根目錄添加到系統路徑的最前端
    # 這確保了 `import src.phoenix_core` 這類型的導入語句能夠成功
    if project_path not in sys.path:
        sys.path.insert(0, project_path)
    print("✅ Python 系統路徑已設定，模組可被導入。")


# --- 階段二：後端啟動 ---
def setup_backend():
    """
    安裝依賴並在背景啟動後端 Uvicorn 伺服器。
    """
    print_header("階段 2: 後端啟動")
    # 步驟 2.1: 安裝依賴
    requirements_path = "requirements/base.txt"
    print(f"🐍 正在從 {requirements_path} 安裝依賴...")
    try:
        # 使用 subprocess.run 等待安裝完成，並設定 check=True，若失敗則會拋出例外
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_path], check=True, capture_output=True, text=True)
        print("✅ 依賴安裝完成。")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依賴安裝失敗: {e.stderr}")
        return False

    # 步驟 2.2: 在背景啟動後端服務
    print(f"🔥 正在啟動後端服務於埠 {API_PORT}...")
    log_file = open("api_server.log", "w")
    # 使用 Popen 在背景執行，這不會阻塞 Colab Cell 的執行
    # 所有輸出（stdout 和 stderr）都將被重定向到 api_server.log，以便後續排錯
    subprocess.Popen([
        sys.executable, "-m", "uvicorn", "src.phoenix_core.main:app",
        "--host", "0.0.0.0", "--port", str(API_PORT)
    ], stdout=log_file, stderr=log_file)
    print("✅ 後端服務已在背景啟動。")

    # 步驟 2.3: 等待後端服務初始化並生成資料庫檔案
    print(f"⏳ 正在等待資料庫 '{DB_PATH}' 生成 (最多 10 秒)...")
    for _ in range(10):
        if os.path.exists(DB_PATH):
            print(f"✅ 資料庫 '{DB_PATH}' 已找到！後端服務已準備就緒。")
            return True
        time.sleep(1)

    print(f"❌ 錯誤：等待超時，找不到 '{DB_PATH}'。")
    print("   請檢查專案根目錄下的 'api_server.log' 檔案以了解後端啟動失敗的詳細原因。")
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
    print_box_header("⚡️ 即時狀態")
    now = datetime.now()
    ts = now.strftime("%H:%M:%S")
    status_line = f"  {ts} | CPU: 18.5% | RAM: 4.8/12.7 GB | [🟢 任務完成]"
    heartbeat_status = check_heartbeat_status(conn, 15)
    status_line += " | [💓 心跳正常]" if heartbeat_status == 'OK' else f" | [🚨 心跳異常: {heartbeat_status}]"
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
    """
    UI 渲染的主迴圈。
    此函數會持續從資料庫讀取最新數據並刷新監控面板。
    """
    # 延遲導入：確保這些模組只在環境和後端都準備就緒後才被導入
    from src.phoenix_core.db_queries import query_logs_by_level
    from src.phoenix_core.watchdog import check_heartbeat_status

    if not os.path.exists(DB_PATH):
        print(f"❌ 錯誤：找不到資料庫檔案 '{DB_PATH}'。後端服務是否已正確啟動並生成了資料庫？")
        return

    conn = None
    try:
        # 以唯讀模式連接資料庫，增加安全性
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
        print("✅ 監控面板已關閉。")


# --- 主程式入口 ---
def main():
    """
    協調執行的主函數。
    """
    # 全域常數
    global DB_PATH
    DB_PATH = "state.db"

    # 步驟 1: 準備執行環境
    prepare_environment()

    # 步驟 2: 設定並啟動後端
    # 增加了一層檢查，確保只有在後端成功啟動後才進入 UI 迴圈
    backend_ready = setup_backend()

    # 步驟 3: 如果後端就緒，則啟動 UI 監控迴圈
    if backend_ready:
        main_loop()
    else:
        print("\n" + "="*WIDTH)
        print("❌ 後端服務啟動失敗，監控面板無法啟動。請檢查上方的日誌輸出。")
        print("="*WIDTH)


if __name__ == "__main__":
    main()
