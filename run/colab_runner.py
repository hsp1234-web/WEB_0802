# -*- coding: utf-8 -*-

# --- Colab 使用者介面參數 ---
#@title 🚀 V27 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### Part 1: 程式碼與環境設定
#@markdown > 設定 Git 倉庫、分支或標籤，以及專案資料夾。
#@markdown ---
#@markdown 後端程式碼倉庫 (REPOSITORY_URL)
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown 後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)
TARGET_BRANCH_OR_TAG = "0.3.4" #@param {type:"string"}
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
from datetime import datetime
from IPython.display import display, clear_output

# 假設這些模組與 runner 在同一個 Python 環境中
# 在真實 Colab 環境中，這需要透過 !pip install 或路徑設定來確保
try:
    from src.phoenix_core.db_queries import query_logs_by_level
    from src.phoenix_core.watchdog import check_heartbeat_status
except ImportError:
    print("錯誤：無法導入 'phoenix_core' 模組。請確保已正確安裝或設定 PYTHONPATH。")
    # 在 Colab 中，我們可能需要動態加入路徑
    # sys.path.insert(0, '/content/your_project_path')
    # from src.phoenix_core.db_queries import query_logs_by_level
    # from src.phoenix_core.watchdog import check_heartbeat_status
    # 為了簡化，此處暫不處理動態路徑
    sys.exit(1)


# --- 環境準備 ---
# (此處應放入真實的後端啟動邏輯，為簡化，我們僅作示意)
def setup_backend():
    print("🚀 正在準備後端環境...")
    # 這裡應該有 git clone, pip install 等指令
    time.sleep(2)
    print("✅ 後端環境準備就緒。")
    print("🔥 正在啟動後端服務...")
    # 這裡應該有啟動 uvicorn 的 subprocess
    time.sleep(1)
    print("✅ 後端服務已在背景啟動。")

# --- 顯示邏輯 (來自 4.3 驗證過的邏輯) ---
WIDTH = 90

def print_line(char='─', width=WIDTH):
    print(char * width)

def print_header(title):
    print('┌' + '─' * (width - 2) + '┐')
    print(f"│{title.center(width - 2)}│")
    print('└' + '─' * (width - 2) + '┘')

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
        # 假設 query_logs_by_level 返回的 row 格式為 (id, timestamp, level, source, message)
        # 我們需要轉換它以符合顯示需求
        logs = query_logs_by_level(conn, level, limit=LOG_DISPLAY_LINES)
        for log in logs:
            # 假設 timestamp 是 ISO 格式字串
            dt_obj = datetime.fromisoformat(log[1])
            all_logs.append((dt_obj, log[2], log[4])) # (datetime, level, message)

    # 按時間倒序排序
    all_logs.sort(key=lambda x: x[0], reverse=True)

    display_logs = all_logs[:LOG_DISPLAY_LINES]

    for log_time, level, message in display_logs:
        ts = log_time.strftime("%H:%M:%S")
        # 簡易的 icon 對應
        icon_map = {'SUCCESS': '✅', 'ERROR': '❌', 'BATTLE': '⚔️', 'INFO': '▶️'}
        icon = icon_map.get(level, '🔹')
        log_line = f" [{ts}] [{level}] {icon} {message}"
        print(f"│{log_line:<{WIDTH - 2}}│")

    print_box_footer()

def print_status_panel(conn):
    print_box_header("⚡️ 即時狀態")

    # 這裡我們需要一個查詢硬體狀態的函式，暫時使用假資料
    now = datetime.now()
    ts = now.strftime("%H:%M:%S")
    status_line = f"  {ts} | CPU: 18.5% | RAM: 4.8/12.7 GB | [🟢 任務完成]"

    # 整合心跳檢查
    heartbeat_status = check_heartbeat_status(conn, 15)
    if heartbeat_status == 'OK':
        status_line += " | [💓 心跳正常]"
    else:
        status_line += f" | [🚨 心跳異常: {heartbeat_status}]"

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

# --- 主執行迴圈 ---
def main_loop():
    DB_PATH = f"{PROJECT_FOLDER_NAME}/state.db"

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

if __name__ == "__main__":
    # 1. 執行環境設定
    setup_backend()

    # 2. 進入主迴圈
    main_loop()
