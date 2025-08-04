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
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>鳳凰之心 - 統一作戰儀表板</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            background-color: transparent; /* 適應 Colab 主題 */
            color: var(--colab-primary-text-color, #d1d5db); /* 使用 Colab 變數 */
        }}
        .font-code {{
            font-family: 'Fira Code', monospace;
        }}
        .dashboard-panel {{
            background-color: var(--colab-secondary-surface-color, transparent);
            border: 1px solid var(--colab-border-color, rgba(71, 85, 105, 0.5));
            border-radius: 0.75rem;
            margin-bottom: 1.5rem;
        }}
        .panel-title {{
            padding: 0.75rem 1.25rem;
            background-color: transparent;
            border-bottom: 1px solid var(--colab-border-color, rgba(71, 85, 105, 0.5));
            border-top-left-radius: 0.75rem;
            border-top-right-radius: 0.75rem;
            color: var(--colab-secondary-text-color, #9ca3af);
            font-weight: 700;
        }}
        .log-container {{
            padding: 1rem;
            font-family: 'Fira Code', monospace;
            font-size: 0.875rem;
            line-height: 1.6;
            height: {log_height}px; /* 由 Python 動態設定 */
            overflow-y: auto;
            display: flex;
            flex-direction: column-reverse;
            background-color: var(--colab-secondary-surface-color, #1e293b);
        }}
        .log-line {{
            display: grid;
            grid-template-columns: 9ch max-content 1fr;
            gap: 1rem;
            align-items: baseline;
        }}
        .log-tag {{
            text-align: center;
            font-weight: 700;
            padding: 0.125rem 0.5rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
        }}
    </style>
</head>
<body class="p-4 sm:p-6 md:p-8">
    <div class="max-w-5xl mx-auto">
        <header class="text-center mb-8">
            <h1 class="text-2xl sm:text-3xl font-bold text-cyan-400">
                🚀 鳳凰之心 - 監控面板 🚀
            </h1>
        </header>

        <section class="dashboard-panel">
            <div class="panel-title">📜 近況彙報</div>
            <div id="log-panel" class="log-container">
                <div class="text-gray-500">正在等待日誌...</div>
            </div>
        </section>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section class="dashboard-panel">
                <div class="panel-title">⚡️ 即時狀態</div>
                <div id="status-panel" class="p-4 font-code text-base sm:text-lg text-center">
                    正在獲取狀態...
                </div>
            </section>

            <section class="dashboard-panel">
                <div class="panel-title">📊 日誌篩選狀態</div>
                <div id="log-status-panel" class="p-4 font-code text-sm">
                    未設定
                </div>
            </section>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section class="dashboard-panel">
                <div class="panel-title">🔗 行動指令</div>
                <div id="action-panel" class="p-4">
                    等待任務完成...
                </div>
            </section>

            <section class="dashboard-panel">
                <div class="panel-title">📋 面板內容操作</div>
                <div class="p-4 flex justify-center">
                    <button id="copy-button" onclick="copyDashboardContent()" class="bg-violet-600 hover:bg-violet-700 text-white font-bold py-2 px-4 rounded-lg transition-all duration-200">
                        複製日誌為純文字
                    </button>
                </div>
            </section>
        </div>
    </div>

<script>
function copyDashboardContent() {
    const container = document.getElementById('log-panel');
    const textToCopy = container.innerText;
    navigator.clipboard.writeText(textToCopy).then(() => {
        const button = document.getElementById('copy-button');
        const originalText = button.innerText;
        button.innerText = '✅ 複製成功!';
        button.classList.remove('bg-violet-600', 'hover:bg-violet-700');
        button.classList.add('bg-green-600');
        setTimeout(() => {
            button.innerText = originalText;
            button.classList.remove('bg-green-600');
            button.classList.add('bg-violet-600', 'hover:bg-violet-700');
        }, 2000);
    }).catch(err => {
        console.error('複製失敗: ', err);
        const button = document.getElementById('copy-button');
        button.innerText = '❌ 複製失敗';
        button.classList.add('bg-red-600');
    });
}
</script>
</body>
</html>
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
            all_logs.append((dt_obj, log[2], log[4])) # time, level, message
    all_logs.sort(key=lambda x: x[0], reverse=True)
    display_logs = all_logs[:LOG_DISPLAY_LINES]

    log_html = ""
    if not display_logs:
        log_html = '<div class="text-gray-500">暫無日誌...</div>'
    else:
        for log_time, level, message in reversed(display_logs):
            ts = log_time.strftime("%H:%M:%S")
            level_upper = level.upper()

            color_map = {
                'SUCCESS': 'bg-green-500/20 text-green-400',
                'ERROR': 'bg-red-500/20 text-red-400',
                'CRITICAL': 'bg-red-700/30 text-red-300 font-bold',
                'BATTLE': 'bg-blue-500/20 text-blue-400',
                'WARN': 'bg-yellow-500/20 text-yellow-400',
                'INFO': 'bg-gray-500/20 text-gray-400',
                'CMD': 'bg-purple-500/20 text-purple-400',
                'LOG_SHELL': 'bg-indigo-500/20 text-indigo-400'
            }
            tag_class = color_map.get(level_upper, 'bg-gray-600/20 text-gray-500')

            escaped_message = html.escape(message)
            log_html += f"""
            <div class="log-line">
                <span class="text-gray-500">[{ts}]</span>
                <span class="log-tag {tag_class}">{level_upper}</span>
                <span class="text-gray-300">{escaped_message}</span>
            </div>
            """

    log_status_html = f"""
    <div class="flex justify-between items-center">
        <span class="font-semibold text-gray-400">當前篩選等級:</span>
        <span class="text-cyan-400 font-mono">{', '.join(levels_to_show) if levels_to_show else '無'}</span>
    </div>
    <div class="flex justify-between items-center mt-2">
        <span class="font-semibold text-gray-400">檢索到的日誌數:</span>
        <span class="text-cyan-400 font-mono">{len(all_logs)}</span>
    </div>
    """
    return log_html, log_status_html

def fetch_status_content(conn):
    now = datetime.now()
    ts = now.strftime("%H:%M:%S")
    cpu_percent = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    ram_used_gb = ram.used / (1024**3)
    ram_total_gb = ram.total / (1024**3)
    heartbeat_status = check_heartbeat_status(conn, 15)

    status_color_map = {
        'OK': 'text-green-400',
        'STOPPED': 'text-yellow-400',
        'NO_HEARTBEAT_YET': 'text-gray-500',
    }
    status_text_map = {
        'OK': '[🟢 核心運行中]',
        'STOPPED': '[🟡 核心已停止]',
        'NO_HEARTBEAT_YET': '[⚪️ 等待心跳...]',
    }

    # Default to error state
    status_color = 'text-red-400'
    main_status = f'[🔴 核心無回應]'

    if heartbeat_status in status_text_map:
        status_color = status_color_map[heartbeat_status]
        main_status = status_text_map[heartbeat_status]
    elif heartbeat_status.startswith('LAGGED'):
        main_status = f'[🟠 心跳延遲 {heartbeat_status.split(":")[1]}s]'
        status_color = 'text-orange-400'

    return f"""
    <div class="flex justify-center items-center space-x-4">
        <span>{ts}</span>
        <span class="text-gray-600">|</span>
        <span>CPU: {cpu_percent:5.1f}%</span>
        <span class="text-gray-600">|</span>
        <span>RAM: {ram_used_gb:.1f}/{ram_total_gb:.1f} GB</span>
        <span class="text-gray-600">|</span>
        <span class="font-bold {status_color}">{main_status}</span>
    </div>
    """

def fetch_action_content():
    line1 = "所有任務已執行完畢！點擊下方連結以開啟互動式操作儀表板。"
    # 這是 Colab 環境，需要一個能在 Colab 外部訪問的 URL
    # google.colab.output.eval_js('google.colab.kernel.proxyPort(port)') 可用來生成
    # 但為了簡化，我們先用一個 placeholder
    url = f"http://localhost:{API_PORT}/"

    return f"""
    <p class="mb-4 text-gray-300">所有任務已執行完畢！點擊下方連結以開啟互動式操作儀表板。</p>
    <a href="{url}" target="_blank" class="text-cyan-400 hover:text-cyan-300 break-all">
        👉 {url}
    </a>
    """

def main_loop():
    DB_PATH = "state.db"
    if not os.path.exists(DB_PATH):
        print(f"❌ 錯誤：找不到資料庫檔案 '{DB_PATH}'。")
        return

    # 動態計算日誌面板高度
    log_height = LOG_DISPLAY_LINES * 25 # 每行約 25px
    final_html = DASHBOARD_HTML.format(log_height=log_height)

    display(HTML(final_html))
    conn = None
    try:
        # 使用 read-only mode 連接
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        while True:
            log_content, log_status_content = fetch_log_content_and_status(conn)
            status_content = fetch_status_content(conn)
            heartbeat_status = check_heartbeat_status(conn, 15)
            action_content = fetch_action_content() if heartbeat_status == 'STOPPED' else '<span class="text-gray-500">等待任務完成...</span>'

            # 將所有內容更新打包成一個 JS 命令
            js_code = f"""
            document.getElementById('log-panel').innerHTML = `{log_content.replace('`', '\\`')}`;
            document.getElementById('status-panel').innerHTML = `{status_content.replace('`', '\\`')}`;
            document.getElementById('log-status-panel').innerHTML = `{log_status_content.replace('`', '\\`')}`;
            document.getElementById('action-panel').innerHTML = `{action_content.replace('`', '\\`')}`;
            """
            display(Javascript(js_code))
            time.sleep(REFRESH_RATE_SECONDS)

    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
             display(Javascript("document.getElementById('status-panel').innerHTML = '<span class=\"text-yellow-400\">🟡 資料庫暫時鎖定，正在重試...</span>';"))
             time.sleep(REFRESH_RATE_SECONDS) # 等待後重試
        else:
             display(Javascript(f"document.getElementById('status-panel').innerHTML = '<span class=\"text-red-400\">❌ 資料庫錯誤: {str(e)}</span>';"))
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
