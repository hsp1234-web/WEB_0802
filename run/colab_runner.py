# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 鳳凰之心 - V34 HTML 專業監控面板                     ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 說明: 此腳本為 Colab 中的主要進入點，用於啟動後端並顯示一個使用   ║
# ║         HTML 和 JavaScript 實現的即時、無閃爍、佈局整齊的監控儀表板。║
# ║ - 依賴: `db_queries.py`, `watchdog.py`, `psutil`, `IPython`        ║
# ║ - 版本: 2.0.0 (專業佈局與日誌狀態面板)                             ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# --- Colab 使用者介面參數 ---
#@title 🚀 V34 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
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
#@markdown **顯示系統日誌 (SHOW_LOG_LEVEL_LOG_SHELL)**
SHOW_LOG_LEVEL_LOG_SHELL = False #@param {type:"boolean"}
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
import psutil
from IPython.display import display, HTML, Javascript

# --- 階段一：環境準備 ---
def prepare_environment():
    base_path = "/content"
    project_path = os.path.join(base_path, PROJECT_FOLDER_NAME)
    print(f"📁 專案目錄設定為: {project_path}")
    if FORCE_REPO_REFRESH and os.path.exists(project_path):
        print(f"🔄 偵測到強制刷新，正在刪除舊目錄...")
        shutil.rmtree(project_path)
        for i in range(5):
            if not os.path.exists(project_path): break
            print(f"   等待目錄刪除... ({i+1}/5)")
            time.sleep(1)
    if not os.path.exists(project_path):
        print(f"克隆儲存庫從 {REPOSITORY_URL} 到 {project_path}...")
        subprocess.run([
            "git", "clone", "--branch", TARGET_BRANCH_OR_TAG,
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

# --- 導入專案模組 ---
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
    print(f"❌ 錯誤：等待超時，找不到 {db_path}。")
    return False

# --- 階段三：HTML UI 顯示邏輯 ---
DASHBOARD_HTML = """
<style>
    .phoenix-dashboard {{ font-family: Menlo, 'Courier New', Courier, monospace; border: 1px solid #ccc; padding: 10px; background-color: #f5f5f5; }}
    .phoenix-table {{ width: 100%; border-collapse: collapse; }}
    .phoenix-table th, .phoenix-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
    .phoenix-table th {{ background-color: #333; color: #fff; }}
    .phoenix-content-box {{ padding: 10px; background-color: #fff; border: 1px solid #ccc; border-radius: 5px; margin-top: 5px; }}
    #log-panel {{ height: 300px; overflow-y: auto; display: flex; flex-direction: column-reverse; background-color: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 5px;}}
    .log-line {{ margin: 0; padding: 2px 0; }}
    #copy-button {{ background-color: #007bff; color: white; border: none; padding: 8px 12px; cursor: pointer; border-radius: 5px; }}
    #copy-button:hover {{ background-color: #0056b3; }}
</style>
<div id="phoenix-main-container" class="phoenix-dashboard">
    <h2 style="text-align: center;">🚀 鳳凰之心 - 監控面板 🚀</h2>
    <table class="phoenix-table">
        <tr>
            <th style="width: 60%;">📜 近況彙報</th>
            <th style="width: 40%;">⚡️ 即時狀態</th>
        </tr>
        <tr>
            <td rowspan="3"><div id="log-panel" class="phoenix-content-box">正在等待日誌...</div></td>
            <td><div id="status-panel" class="phoenix-content-box">正在獲取狀態...</div></td>
        </tr>
        <tr>
            <th>📊 日誌篩選狀態</th>
        </tr>
        <tr>
            <td><div id="log-status-panel" class="phoenix-content-box">未設定</div></td>
        </tr>
        <tr>
            <th>🔗 行動指令</th>
            <th>📋 面板內容操作</th>
        </tr>
        <tr>
            <td><div id="action-panel" class="phoenix-content-box">等待任務完成...</div></td>
            <td><div class="phoenix-content-box"><button id="copy-button" onclick="copyDashboardContent()">複製日誌為純文字</button></div></td>
        </tr>
    </table>
</div>
<script>
function copyDashboardContent() {
    const container = document.getElementById('log-panel');
    const textToCopy = container.innerText;
    navigator.clipboard.writeText(textToCopy).then(() => {
        const button = document.getElementById('copy-button');
        const originalText = button.innerText;
        button.innerText = '✅ 複製成功!';
        setTimeout(() => { button.innerText = originalText; }, 2000);
    }).catch(err => { console.error('複製失敗: ', err); });
}
</script>
"""

def get_selected_log_levels():
    levels = []
    if SHOW_LOG_LEVEL_BATTLE: levels.append('BATTLE')
    if SHOW_LOG_LEVEL_SUCCESS: levels.append('SUCCESS')
    if SHOW_LOG_LEVEL_INFO: levels.append('INFO')
    if SHOW_LOG_LEVEL_CMD: levels.append('CMD')
    if SHOW_LOG_LEVEL_LOG_SHELL: levels.append('LOG_SHELL')
    if SHOW_LOG_LEVEL_ERROR: levels.append('ERROR')
    if SHOW_LOG_LEVEL_CRITICAL: levels.append('CRITICAL')
    if SHOW_LOG_LEVEL_PERF: levels.append('PERF')
    return levels

def fetch_log_content_and_status(conn):
    levels_to_show = get_selected_log_levels()
    all_logs = []
    for level in levels_to_show:
        logs = query_logs_by_level(conn, level, limit=LOG_DISPLAY_LINES)
        for log in logs:
            dt_obj = datetime.fromisoformat(log[1].replace('Z', '+00:00'))
            all_logs.append((dt_obj, log[2], log[4]))
    all_logs.sort(key=lambda x: x[0], reverse=True)
    display_logs = all_logs[:LOG_DISPLAY_LINES]

    log_html = ""
    for log_time, level, message in reversed(display_logs):
        ts = log_time.strftime("%H:%M:%S")
        icon_map = {'SUCCESS': '✅', 'ERROR': '❌', 'BATTLE': '⚔️', 'INFO': '▶️', 'CRITICAL': '🚨'}
        icon = icon_map.get(level, '🔹')
        escaped_message = html.escape(message)
        log_html += f'<div class="log-line">[{ts}] [{level}] {icon} {escaped_message}</div>'

    log_status_html = f"<b>當前篩選等級:</b> {', '.join(levels_to_show)}<br>"
    log_status_html += f"<b>共檢索到日誌:</b> {len(all_logs)} 條"

    return log_html, log_status_html

def fetch_status_content(conn):
    now = datetime.now()
    ts = now.strftime("%H:%M:%S")
    cpu_percent = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    ram_used_gb = ram.used / (1024**3)
    ram_total_gb = ram.total / (1024**3)
    heartbeat_status = check_heartbeat_status(conn, 15)

    if heartbeat_status == 'OK':
        main_status = "<span style='color: green;'>[🟢 核心運行中]</span>"
        heartbeat_text = "<span style='color: green;'>[💓 心跳正常]</span>"
    else:
        main_status = "<span style='color: red;'>[🔴 核心無回應]</span>"
        heartbeat_text = f"<span style='color: red;'>[🚨 心跳異常: {heartbeat_status}]</span>"

    status_line = f"{ts} | CPU: {cpu_percent:5.1f}% | RAM: {ram_used_gb:.1f}/{ram_total_gb:.1f} GB<br>{main_status} {heartbeat_text}"
    return status_line

def fetch_action_content():
    line1 = "所有任務已執行完畢！點擊下方連結以開啟互動式操作儀表板。"
    line2 = f"👉 http://localhost:{API_PORT}/"
    return f"{html.escape(line1)}<br><br>{html.escape(line2)}"

def main_loop():
    DB_PATH = "state.db"
    if not os.path.exists(DB_PATH):
        print(f"❌ 錯誤：找不到資料庫檔案 '{DB_PATH}'。")
        return

    display(HTML(DASHBOARD_HTML))
    conn = None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        while True:
            log_content, log_status_content = fetch_log_content_and_status(conn)
            status_content = fetch_status_content(conn)
            heartbeat_status = check_heartbeat_status(conn, 15)
            action_content = fetch_action_content() if heartbeat_status == 'STOPPED' else '等待任務完成...'

            js_code = f"""
            document.getElementById('log-panel').innerHTML = `{log_content.replace('`', '\\`')}`;
            document.getElementById('status-panel').innerHTML = `{status_content.replace('`', '\\`')}`;
            document.getElementById('log-status-panel').innerHTML = `{log_status_content.replace('`', '\\`')}`;
            document.getElementById('action-panel').innerHTML = `{action_content.replace('`', '\\`')}`;
            """
            display(Javascript(js_code))
            time.sleep(REFRESH_RATE_SECONDS)

    except sqlite3.Error as e:
        display(Javascript(f"document.getElementById('status-panel').innerHTML = '❌ 資料庫錯誤: {str(e)}';"))
    except KeyboardInterrupt:
        display(Javascript("document.getElementById('status-panel').innerHTML = '🛑 使用者手動中斷。';"))
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if setup_backend():
        main_loop()
