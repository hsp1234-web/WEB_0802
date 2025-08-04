# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 鳳凰之心 - V33 HTML 動態監控面板                     ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 說明: 此腳本為 Colab 中的主要進入點，用於啟動後端並顯示一個使用   ║
# ║         HTML 和 JavaScript 實現的即時、無閃爍監控儀表板。          ║
# ║ - 依賴: `db_queries.py`, `watchdog.py`, `psutil`, `IPython`        ║
# ║ - 版本: 1.0.0 (HTML/JS 重構版)                                     ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# --- Colab 使用者介面參數 ---
#@title 🚀 V33 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### Part 1: 程式碼與環境設定
#@markdown > 設定 Git 倉庫、分支或標籤，以及專案資料夾。
#@markdown ---
#@markdown 後端程式碼倉庫 (REPOSITORY_URL)
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown 後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)
TARGET_BRANCH_OR_TAG = "0.4.9" #@param {type:"string"}
#@markdown 專案資料夾名稱 (PROJECT_FOLDER_NAME)
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown 強制刷新後端程式碼 (FORCE_REPO_REFRESH)
FORCE_REPO_REFRESH = True #@param {type:"boolean"}

#@markdown ---
#@markdown ### Part 2: 應用程式參數
#@markdown > 設定指揮中心的核心運行參數。
#@markdown ---
#@markdown 儀表板更新頻率 (秒) (REFRESH_RATE_SECONDS)
REFRESH_RATE_SECONDS = 1.5 #@param {type:"number"}
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
import html
import psutil # 用於獲取系統資源使用率
from IPython.display import display, HTML, Javascript

# --- 階段一：環境準備 ---
def prepare_environment():
    base_path = "/content"
    project_path = os.path.join(base_path, PROJECT_FOLDER_NAME)
    print(f"📁 專案目錄設定為: {project_path}")
    if FORCE_REPO_REFRESH and os.path.exists(project_path):
        print(f"🔄 偵測到強制刷新，正在刪除舊目錄...")
        shutil.rmtree(project_path)
        # 增加一個健壯的等待迴圈，確保目錄被完全刪除後再繼續
        for i in range(5):
            if not os.path.exists(project_path):
                break
            print(f"   等待目錄刪除... ({i+1}/5)")
            time.sleep(1)
    if not os.path.exists(project_path):
        print(f"克隆儲存庫從 {REPOSITORY_URL} 到 {project_path}...")
        subprocess.run([
            "git", "clone", "--depth", "1", "--branch", TARGET_BRANCH_OR_TAG,
            REPOSITORY_URL, project_path
        ], check=True)
    else:
        print("✅ 專案目錄已存在，跳過下載。")
    os.chdir(project_path)
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
    print("🚀 正在準備後端環境...")
    requirements_path = "requirements/base.txt"
    print(f"--- 正在從 {requirements_path} 安裝依賴... ---")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_path], check=True, capture_output=True, text=True)
        print("✅ 依賴安裝完成。")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依賴安裝失敗: {e.stderr}")
        return False
    print(f"🔥 正在啟動後端服務於埠 {API_PORT}...")
    log_file = open("api_server.log", "w")
    subprocess.Popen([
        sys.executable, "-m", "uvicorn", "src.phoenix_core.main:app",
        "--host", "0.0.0.0", "--port", str(API_PORT)
    ], stdout=log_file, stderr=log_file)
    print("✅ 後端服務已在背景啟動。")
    print("--- 等待 state.db 生成 (最多 15 秒)... ---")
    db_path = "state.db"
    for _ in range(15):
        if os.path.exists(db_path):
            print("✅ state.db 已找到！")
            return True
        time.sleep(1)
    print(f"❌ 錯誤：等待超時，找不到 {db_path}。請檢查 api_server.log 以了解後端啟動詳情。")
    return False

# --- 階段三：HTML UI 顯示邏輯 ---

# 靜態 HTML 骨架
DASHBOARD_HTML = """
<style>
    .phoenix-dashboard {{ font-family: 'Courier New', Courier, monospace; border: 1px solid #ccc; padding: 10px; background-color: #f5f5f5; }}
    .phoenix-box {{ border: 1px solid #aaa; border-radius: 5px; margin-top: 10px; background-color: #fff; }}
    .phoenix-header {{ background-color: #333; color: #fff; padding: 5px 10px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
    .phoenix-content {{ padding: 10px; white-space: pre-wrap; }}
    #log-panel {{ height: 300px; overflow-y: auto; display: flex; flex-direction: column-reverse; }}
    .log-line {{ margin: 0; padding: 2px 0; }}
    #copy-button {{ background-color: #007bff; color: white; border: none; padding: 8px 12px; text-align: center; text-decoration: none; display: inline-block; font-size: 14px; margin-top: 10px; cursor: pointer; border-radius: 5px; }}
    #copy-button:hover {{ background-color: #0056b3; }}
</style>
<div id="phoenix-main-container" class="phoenix-dashboard">
    <div class="phoenix-header">🚀 鳳凰之心 - 監控面板 🚀</div>

    <div class="phoenix-box">
        <div class="phoenix-header">📜 近況彙報</div>
        <div id="log-panel" class="phoenix-content">正在等待日誌...</div>
    </div>

    <div class="phoenix-box">
        <div class="phoenix-header">⚡️ 即時狀態</div>
        <div id="status-panel" class="phoenix-content">正在獲取狀態...</div>
    </div>

    <div class="phoenix-box">
        <div class="phoenix-header">🔗 行動指令</div>
        <div id="action-panel" class="phoenix-content">等待任務完成...</div>
    </div>

    <div class="phoenix-box">
        <div class="phoenix-header">📋 面板內容操作</div>
        <div class="phoenix-content">
            <button id="copy-button" onclick="copyDashboardContent()">複製完整輸出為純文字</button>
        </div>
    </div>
</div>

<script>
function copyDashboardContent() {
    const container = document.getElementById('phoenix-main-container');
    const textToCopy = container.innerText;
    navigator.clipboard.writeText(textToCopy).then(() => {
        const button = document.getElementById('copy-button');
        const originalText = button.innerText;
        button.innerText = '✅ 複製成功!';
        setTimeout(() => { button.innerText = originalText; }, 2000);
    }).catch(err => {
        console.error('複製失敗: ', err);
    });
}
</script>
"""

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

def fetch_log_content(conn):
    levels_to_show = get_selected_log_levels()
    all_logs = []
    for level in levels_to_show:
        logs = query_logs_by_level(conn, level, limit=LOG_DISPLAY_LINES)
        for log in logs:
            # 假設 log[1] 是 ISO 格式的時間戳，log[2] 是等級，log[4] 是訊息
            dt_obj = datetime.fromisoformat(log[1].replace('Z', '+00:00'))
            all_logs.append((dt_obj, log[2], log[4]))
    all_logs.sort(key=lambda x: x[0], reverse=True)
    display_logs = all_logs[:LOG_DISPLAY_LINES]

    log_html = ""
    for log_time, level, message in reversed(display_logs): # 反轉以實現從頂部新增
        ts = log_time.strftime("%H:%M:%S")
        icon_map = {'SUCCESS': '✅', 'ERROR': '❌', 'BATTLE': '⚔️', 'INFO': '▶️', 'CRITICAL': '🚨'}
        icon = icon_map.get(level, '🔹')
        escaped_message = html.escape(message)
        log_html += f'<div class="log-line">[{ts}] [{level}] {icon} {escaped_message}</div>'
    return log_html

def fetch_status_content(conn):
    now = datetime.now()
    ts = now.strftime("%H:%M:%S")
    cpu_percent = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    ram_used_gb = ram.used / (1024**3)
    ram_total_gb = ram.total / (1024**3)
    heartbeat_status = check_heartbeat_status(conn, 15)

    if heartbeat_status == 'OK':
        main_status = "[🟢 核心運行中]"
        heartbeat_text = "[💓 心跳正常]"
    else:
        main_status = "[🔴 核心無回應]"
        heartbeat_text = f"[🚨 心跳異常: {heartbeat_status}]"

    status_line = f"{ts} | CPU: {cpu_percent:5.1f}% | RAM: {ram_used_gb:.1f}/{ram_total_gb:.1f} GB | {main_status} {heartbeat_text}"
    return html.escape(status_line)

def fetch_action_content():
    line1 = "所有任務已執行完畢！點擊下方連結以開啟互動式操作儀表板。"
    line2 = f"👉 http://localhost:{API_PORT}/"
    return f"{html.escape(line1)}<br><br>{html.escape(line2)}"

# --- 階段四：主執行迴圈 ---
def main_loop():
    DB_PATH = "state.db"
    if not os.path.exists(DB_PATH):
        print(f"❌ 錯誤：找不到資料庫檔案 '{DB_PATH}'。")
        return

    # 1. 先顯示靜態的 HTML 骨架
    display(HTML(DASHBOARD_HTML))

    conn = None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        while True:
            # 2. 獲取動態內容
            log_content_js = fetch_log_content(conn).replace('`', '\\`')
            status_content_js = fetch_status_content(conn).replace('`', '\\`')
            # 假設任務完成後，心跳會停止
            heartbeat_status = check_heartbeat_status(conn, 15)
            action_content_js = fetch_action_content().replace('`', '\\`') if heartbeat_status == 'STOPPED' else '等待任務完成...'

            # 3. 組合並執行 JavaScript 來更新 UI
            js_code = f"""
            document.getElementById('log-panel').innerHTML = `{log_content_js}`;
            document.getElementById('status-panel').innerHTML = `{status_content_js}`;
            document.getElementById('action-panel').innerHTML = `{action_content_js}`;
            """
            display(Javascript(js_code))

            time.sleep(REFRESH_RATE_SECONDS)

    except sqlite3.Error as e:
        js_code = f"document.getElementById('status-panel').innerHTML = '❌ 資料庫錯誤: {str(e)}';"
        display(Javascript(js_code))
    except KeyboardInterrupt:
        js_code = "document.getElementById('status-panel').innerHTML = '🛑 使用者手動中斷。';"
        display(Javascript(js_code))
    finally:
        if conn:
            conn.close()

# --- 主程式入口 ---
if __name__ == "__main__":
    if setup_backend():
        main_loop()
