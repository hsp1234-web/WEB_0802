# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║             🚀 Colab 指揮中心 V25 (穩定埠號版)                     ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 新功能：動態尋找可用埠號，解決 `Address already in use` 問題。   ║
# ║   - 新功能：儀表板內建「複製純文字狀態」按鈕，方便手機操作。         ║
# ║   - 職責：啟動並以動態 HTML 儀表板持續監控後端服務。                 ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import sqlite3
import json
from IPython.display import display, HTML, clear_output
import pytz
from datetime import datetime
import threading
from collections import deque
import asyncio

try:
    import yaml
    import httpx
    from google.colab import output as colab_output
    import nest_asyncio
    from aiohttp import web
except ImportError:
    print("正在安裝指揮中心核心依賴 (PyYAML, httpx, nest_asyncio, aiohttp)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml", "httpx", "nest_asyncio", "aiohttp"])
    import yaml
    import httpx
    from google.colab import output as colab_output
    import nest_asyncio
    from aiohttp import web

# from core_utils.port_manager import find_available_port, kill_processes_using_port

nest_asyncio.apply()

#@title 🚀 v25 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 程式碼與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤，以及專案資料夾。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/0721_web" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "6.6.5" #@param {type:"string"}
#@markdown **專案資料夾名稱 (PROJECT_FOLDER_NAME)**
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown **強制刷新後端程式碼 (FORCE_REPO_REFRESH)**
FORCE_REPO_REFRESH = True #@param {type:"boolean"}

#@markdown ---
#@markdown ### **Part 2: 應用程式參數**
#@markdown > **設定指揮中心的核心運行參數。**
#@markdown ---
#@markdown **儀表板更新頻率 (秒) (REFRESH_RATE_SECONDS)**
REFRESH_RATE_SECONDS = 1.0 #@param {type:"number"}
#@markdown **效能監控更新頻率 (秒) (PERFORMANCE_MONITOR_RATE_SECONDS)**
PERFORMANCE_MONITOR_RATE_SECONDS = 0.5 #@param {type:"number"}
#@markdown **日誌歸檔資料夾 (LOG_ARCHIVE_FOLDER_NAME)**
LOG_ARCHIVE_FOLDER_NAME = "作戰日誌歸檔" #@param {type:"string"}
#@markdown **時區設定 (TIMEZONE)**
TIMEZONE = "Asia/Taipei" #@param {type:"string"}
#@markdown **快速測試模式 (FAST_TEST_MODE)**
FAST_TEST_MODE = False #@param {type:"boolean"}

#@markdown ---
#@markdown ### **Part 3: 日誌顯示設定**
#@markdown > **選擇您想在儀表板上看到的日誌等級。**
#@markdown ---
#@markdown **日誌顯示行數 (LOG_DISPLAY_LINES)**
LOG_DISPLAY_LINES = 50 #@param {type:"integer"}
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

#@markdown ---
#@markdown ### **Part 4: Colab 連線設定**
#@markdown > **設定如何獲取 Colab 的公開代理網址。**
#@markdown ---
#@markdown **URL 獲取重試次數 (COLAB_URL_RETRIES)**
COLAB_URL_RETRIES = 12 #@param {type:"integer"}
#@markdown **URL 獲取重試延遲 (秒) (COLAB_URL_RETRY_DELAY)**
COLAB_URL_RETRY_DELAY = 5 #@param {type:"integer"}

#@markdown ---
#@markdown > **設定完成後，點擊此儲存格左側的「執行」按鈕。**
#@markdown ---

# ==============================================================================
# 🚀 核心邏輯
# ==============================================================================

shared_status = {
    "current_task": "初始化中...",
    "logs": deque(maxlen=LOG_DISPLAY_LINES),
    "api_port": None,
    "launch_process": None,
    "project_path": None,
    "worker_error": None,
}
status_lock = threading.Lock()
api_app_runner = None

def update_status(task=None, log=None, api_port=None):
    with status_lock:
        if task is not None:
            shared_status["current_task"] = task
        if log is not None:
            shared_status["logs"].append(f"[{datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}] {log}")
        if api_port is not None:
            shared_status["api_port"] = api_port

def background_worker():
    """在背景執行緒中處理所有耗時任務"""
    project_path = None
    try:
        # --- 專案路徑設定 ---
        # 這裡的路徑是 Colab 環境特有的結構
        base_path = Path("/content")
        project_path = base_path / PROJECT_FOLDER_NAME
        with status_lock:
            shared_status["project_path"] = project_path

        # --- 步驟 1: 準備專案環境 ---
        update_status(task="準備專案環境")
        if FORCE_REPO_REFRESH and project_path.exists():
            update_status(log="偵測到強制刷新，正在刪除舊的專案資料夾...")
            shutil.rmtree(project_path)
            update_status(log="✅ 舊資料夾已刪除。")

        if not project_path.exists():
            update_status(log="正在從 Github 下載程式碼...")
            # 使用 subprocess 執行 git clone
            process = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", TARGET_BRANCH_OR_TAG, REPOSITORY_URL, str(project_path)],
                capture_output=True, text=True, check=True
            )
            update_status(log="✅ 程式碼下載成功。")
        else:
            update_status(log="專案資料夾已存在，跳過下載。")

        # --- 步驟 2: 安裝專案套件 ---
        update_status(task="安裝專案套件")
        # 這是套件化方案的核心步驟
        # 我們在下載下來的專案目錄中執行 `pip install -e .`
        # 這會讓 `core_utils`, `scripts` 等模組在整個環境中都可被 import
        install_process = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            cwd=project_path,
            capture_output=True, text=True, check=True
        )
        update_status(log="✅ 專案已在可編輯模式下安裝成功。")

        # --- 步驟 3: 生成設定檔 ---
        # (此步驟邏輯不變)
        update_status(task="生成專案設定檔")
        api_port = shared_status.get("api_port")
        config_data = {
            "REFRESH_RATE_SECONDS": REFRESH_RATE_SECONDS,
            "PERFORMANCE_MONITOR_RATE_SECONDS": PERFORMANCE_MONITOR_RATE_SECONDS,
            "LOG_DISPLAY_LINES": LOG_DISPLAY_LINES,
            "LOG_ARCHIVE_FOLDER_NAME": LOG_ARCHIVE_FOLDER_NAME,
            "TIMEZONE": TIMEZONE,
            "FAST_TEST_MODE": FAST_TEST_MODE,
            "LOG_LEVELS_TO_SHOW": {
                level: globals()[f"SHOW_LOG_LEVEL_{level.upper()}"]
                for level in ["BATTLE", "SUCCESS", "INFO", "CMD", "SHELL", "ERROR", "CRITICAL", "PERF"]
                if globals()[f"SHOW_LOG_LEVEL_{level.upper()}"]
            },
            "COLAB_URL_RETRIES": COLAB_URL_RETRIES,
            "COLAB_URL_RETRY_DELAY": COLAB_URL_RETRY_DELAY,
            "INTERNAL_API_PORT": api_port,
        }
        config_file = project_path / "config.json"
        config_file.write_text(json.dumps(config_data, indent=4, ensure_ascii=False))
        update_status(log=f"✅ Colab 設定檔 (config.json) 已生成。")

        # --- 步驟 4: 啟動後端服務 (重構後) ---
        update_status(task="啟動後端服務")
        db_file_path = project_path / "state.db"

        # 由於專案已安裝，我們現在可以直接 import
        from scripts import launch

        update_status(log="🚀 使用模組化方式啟動後端...")
        # 直接呼叫 launch.py 的 main 函式
        # 注意：launch.main 是 async，所以我們需要用 asyncio.run 來執行
        # 這會在當前執行緒中啟動並運行 asyncio 事件循環
        asyncio.run(launch.main(db_path=db_file_path))

        # 因為 launch.main 會持續運行直到被中斷，所以下面的程式碼可能不會立即執行
        update_status(log="✅ 後端服務已停止。")
        update_status(task="後端服務已結束")

    except subprocess.CalledProcessError as e:
        # 處理 git 或 pip 的錯誤
        error_message = f"❌ 子程序執行失敗: {e.stderr}"
        update_status(task="背景任務發生致命錯誤", log=error_message)
        with status_lock:
            shared_status["worker_error"] = e.stderr
    except Exception as e:
        # 處理其他所有錯誤
        error_message = f"❌ {e}"
        update_status(task="背景任務發生致命錯誤", log=error_message)
        with status_lock:
            shared_status["worker_error"] = str(e)


def render_dashboard_html(api_port):
    # ... (HTML and CSS are mostly the same)
    # The key change is to pass the dynamic port to the JavaScript
    refresh_interval_ms = int(REFRESH_RATE_SECONDS * 1000)
    css = """
    <style>
        body { background-color: #1a1a1a; color: #e0e0e0; font-family: 'Noto Sans TC', 'Fira Code', monospace; }
        .container { padding: 1em; }
        .panel { border: 1px solid #444; margin-bottom: 1em; }
        .title { font-weight: bold; padding: 0.5em; border-bottom: 1px solid #444; background-color: #2a2a2a;}
        .content { padding: 0.5em; }
        .grid { display: grid; grid-template-columns: 1fr 2fr; gap: 1em; }
        .log { font-size: 0.9em; white-space: pre-wrap; word-break: break-all; }
        .footer { text-align: center; padding-top: 1em; border-top: 1px solid #444; font-size: 0.8em; color: #888;}
        table { width: 100%;}
        .log-entry { margin-bottom: 5px; }
        .log-level-BATTLE { color: #82aaff; }
        .log-level-SUCCESS { color: #c3e88d; }
        .log-level-ERROR, .log-level-CRITICAL { color: #ff5370; }
        .log-level-INFO { color: #89ddff; }
        .log-level-WARN { color: #ffcb6b; }
        .colab-link-panel { display: none; padding: 0.8em; margin-bottom: 1em; background-color: #2c3e50; border: 1px solid #3498db; border-radius: 5px; text-align: center; font-size: 1.1em; }
        .colab-link-panel strong { color: #ffffff; }
        .colab-link-panel a { color: #f1c40f; font-weight: bold; text-decoration: none; }
        .colab-link-panel a:hover { text-decoration: underline; }
        #entry-point-panel { display: none; grid-column: 1 / -1; text-align: center; padding: 1em; background-color: #2d2d2d; border: 1px solid #50fa7b; }
        #entry-point-button { display: inline-block; padding: 10px 20px; font-size: 1.2em; font-weight: bold; color: #1a1a1a; background-color: #50fa7b; border: none; border-radius: 5px; text-decoration: none; cursor: pointer; }
        #copy-status-button { margin-top: 10px; padding: 8px 15px; font-size: 1em; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }
    </style>
    """
    html_body = """
    <div class="container">
        <div id="colab-link-container" class="colab-link-panel">
             🔗 <strong>Colab 代理連結:</strong> <a href="#" id="colab-proxy-link" target="_blank">正在生成中...</a>
        </div>
        <div class="grid">
            <div>
                <div class="panel">
                    <div class="title">微服務狀態</div>
                    <div class="content"><table id="app-status-table"><tbody><tr><td>等待後端回報...</td></tr></tbody></table></div>
                </div>
                <div class="panel">
                    <div class="title">系統資源 (由後端回報)</div>
                    <div class="content">
                        <table>
                            <tr><td>CPU</td><td id="cpu-usage">0.0%</td></tr>
                            <tr><td>RAM</td><td id="ram-usage">0.0%</td></tr>
                        </table>
                    </div>
                </div>
            </div>
            <div class="panel">
                <div class="title">啟動程序日誌</div>
                <div class="content log" id="log-container">等待日誌...</div>
            </div>
        </div>
        <div id="entry-point-panel">
             <a id="entry-point-button" href="#" target="_blank">🚀 進入主控台</a>
             <p style="font-size:0.9em; margin-top: 8px;">主儀表板已就緒，點擊上方按鈕進入操作介面。</p>
        </div>
        <div class="footer" id="footer-status">指揮中心前端任務: 初始化中...</div>
        <div style="text-align: center; margin-top: 1em;">
            <button id="copy-status-button" onclick="copyStatusAsText()">📋 複製純文字狀態</button>
        </div>
    </div>
    """
    javascript = f"""
    <script type="text/javascript">
        let currentStatusData = {{}};
        const statusMap = {{
            "running": "🟢 運行中", "pending": "🟡 等待中",
            "installing": "🛠️ 安裝中", "starting": "🚀 啟動中",
            "failed": "🔴 失敗", "unknown": "❓ 未知"
        }};
        const apiUrl = `http://localhost:{api_port}/api/v1/status`;

        // ... (rest of the javascript is the same as before)
        function formatStatus(data) {{
            if (!data || !data.status) {{
                return "狀態資訊不完整，無法生成報告。";
            }}
            let text = `鳳凰之心狀態報告 (即時)\\n`;
            text += `========================\\n`;
            text += `後端任務階段: ${{data.status.current_stage || 'N/A'}}\\n`;
            text += `CPU: ${{data.status.cpu_usage ? data.status.cpu_usage.toFixed(1) : 'N/A'}}%, RAM: ${{data.status.ram_usage ? data.status.ram_usage.toFixed(1) : 'N/A'}}%\\n\\n`;
            text += `微服務狀態:\\n`;
            try {{
                const apps = JSON.parse(data.status.apps_status || '{{}}');
                if (Object.keys(apps).length > 0) {{
                     for (const [name, status] of Object.entries(apps)) {{
                        text += `- ${{name}}: ${{statusMap[status] || status}}\\n`;
                    }}
                }} else {{
                    text += `- 尚無服務狀態回報\\n`;
                }}
            }} catch (e) {{
                text += `- 無法解析服務狀態\\n`;
            }}

            text += `\\n最新日誌:\\n`;
            if (data.logs && data.logs.length > 0) {{
                data.logs.forEach(log => {{
                    text += `[${{new Date(log.timestamp).toLocaleTimeString()}}] [${{log.level}}] ${{log.message}}\\n`;
                }});
            }} else {{
                text += `尚無日誌紀錄\\n`;
            }}
            return text;
        }}

        function copyToClipboard(text) {{
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            try {{
                document.execCommand('copy');
            }} catch (err) {{
                console.error('無法自動複製到剪貼簿', err);
                alert('複製失敗，您的瀏覽器可能不支援此操作。');
            }}
            document.body.removeChild(textarea);
        }}

        function copyStatusAsText() {{
            const button = document.getElementById('copy-status-button');
            const originalText = button.textContent;
            const textToCopy = formatStatus(currentStatusData);
            copyToClipboard(textToCopy);
            button.textContent = '已複製！';
            setTimeout(() => {{
                button.textContent = originalText;
            }}, 2000);
        }}

        function updateDashboard() {{
            fetch(apiUrl)
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error('後端服務尚未就緒...');
                    }}
                    return response.json();
                }})
                .then(data => {{
                    currentStatusData = data; // 維護全域狀態

                    // 更新系統資源
                    document.getElementById('cpu-usage').textContent = `${{data.status.cpu_usage ? data.status.cpu_usage.toFixed(1) : '0.0'}}%`;
                    document.getElementById('ram-usage').textContent = `${{data.status.ram_usage ? data.status.ram_usage.toFixed(1) : '0.0'}}%`;

                    // 更新微服務狀態
                    const appStatusTable = document.getElementById('app-status-table').querySelector('tbody');
                    let apps = {{}};
                    try {{
                        apps = JSON.parse(data.status.apps_status || '{{}}');
                    }} catch(e) {{}}

                    let appRows = '';
                    if (Object.keys(apps).length > 0) {{
                        for (const [appName, status] of Object.entries(apps)) {{
                            const statusText = statusMap[status] || statusMap['unknown'];
                            appRows += `<tr><td>${{appName.charAt(0).toUpperCase() + appName.slice(1)}}</td><td>${{statusText}}</td></tr>`;
                        }}
                    }} else {{
                        appRows = '<tr><td>等待後端回報...</td></tr>';
                    }}
                    appStatusTable.innerHTML = appRows;

                    // 更新日誌
                    const logContainer = document.getElementById('log-container');
                    let logEntries = '';
                    if (data.logs && data.logs.length > 0) {{
                        const reversedLogs = [...data.logs].reverse();
                        reversedLogs.forEach(log => {{
                            const time = new Date(log.timestamp).toLocaleTimeString('en-GB');
                            logEntries += `<div class="log-entry"><span class="log-level-${{log.level}}">[${{time}}] [${{log.level}}]</span> ${{log.message}}</div>`;
                        }});
                    }} else {{
                        logEntries = '等待日誌...';
                    }}
                    logContainer.innerHTML = logEntries;

                    // 更新頁腳和主控台入口
                    const footer = document.getElementById('footer-status');
                    const entryPointPanel = document.getElementById('entry-point-panel');
                    const entryPointButton = document.getElementById('entry-point-button');
                    const colabLinkContainer = document.getElementById('colab-link-container');
                    const colabProxyLink = document.getElementById('colab-proxy-link');

                    if (data.status.action_url) {{
                        colabLinkContainer.style.display = 'block';
                        colabProxyLink.href = data.status.action_url;
                        colabProxyLink.textContent = data.status.action_url;
                        entryPointPanel.style.display = 'block';
                        entryPointButton.href = data.status.action_url;
                        footer.textContent = `指揮中心後端任務: ${{data.status.current_stage || '所有服務運行中'}}`;
                    }} else {{
                        colabLinkContainer.style.display = 'none';
                        entryPointPanel.style.display = 'none';
                        footer.textContent = `指揮中心後端任務: ${{data.status.current_stage || '執行中...'}}`;
                    }}
                }})
                .catch(error => {{
                    const footer = document.getElementById('footer-status');
                    footer.textContent = `前端狀態: ${{error.message}}`;
                    currentStatusData = {{ error: error.message }}; // 清除舊數據
                }});
        }}

        // 立即執行一次，然後設定定時器
        updateDashboard();
        setInterval(updateDashboard, {refresh_interval_ms});
    </script>
    """
    return css + html_body + javascript

async def start_api_server(port):
    # ... (This will be the new aiohttp server logic)
    global api_app_runner
    app = web.Application()
    # The handlers will now be part of this script
    async def get_status(request):
        with status_lock:
            # This needs to be adapted to fetch from the new DB structure in launch.py
            # For now, return the local shared_status
            return web.json_response(shared_status)

    async def shutdown_api(request):
        update_status(log="接收到 API 關閉指令，準備關閉服務...")
        # This will now need to find and terminate the launch.py process
        with status_lock:
            p = shared_status.get("launch_process")
            if p:
                p.terminate()
        return web.json_response({"status": "shutdown_initiated"})

    app.router.add_get("/api/v1/status", get_status)
    app.router.add_post("/api/v1/shutdown", shutdown_api)

    api_app_runner = web.AppRunner(app)
    await api_app_runner.setup()
    site = web.TCPSite(api_app_runner, 'localhost', port)
    await site.start()
    update_status(log=f"內部 API 伺服器已在 http://localhost:{port} 啟動")
    await asyncio.Event().wait()


def main():
    from core_utils.port_manager import find_available_port, kill_processes_using_port
    # 1. 清理舊程序並尋找可用埠號
    DEFAULT_PORT = 8088
    update_status(log=f"正在清理可能殘留的舊程序 (埠號: {DEFAULT_PORT})...")
    kill_processes_using_port(DEFAULT_PORT)

    api_port = find_available_port(start_port=DEFAULT_PORT)
    if not api_port:
        update_status(log="❌ 致命錯誤：找不到可用的 API 埠號。")
        return
    update_status(api_port=api_port)

    # 2. 啟動儀表板
    update_status(log=f"指揮中心 V25 (穩定埠號版) 啟動。將使用埠號: {api_port}")
    clear_output(wait=True)
    display(HTML(render_dashboard_html(api_port)))

    # 3. 在背景執行緒中啟動後端任務
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()

    # 4. 啟動 URL 服務
    url_service_thread = threading.Thread(
        target=lambda: asyncio.run(serve_proxy_url_with_retry(
            health_check_url="http://localhost:8000/health",
            port=8000,
            retries=COLAB_URL_RETRIES,
            delay=COLAB_URL_RETRY_DELAY
        )),
        daemon=True
    )
    url_service_thread.start()

    # 5. 主執行緒等待，直到被中斷
    try:
        while True:
            time.sleep(1)
            # 在這裡我們可以檢查 worker_thread 是否出現錯誤
            with status_lock:
                if shared_status["worker_error"]:
                    print(f"背景工作發生錯誤: {shared_status['worker_error']}")
                    break
    except KeyboardInterrupt:
        print("\n🛑 操作已被使用者手動中斷。")
    finally:
        # 清理 launch.py 程序
        with status_lock:
            p = shared_status.get("launch_process")
            if p and p.poll() is None:
                print("正在終止後端 launch.py 程序...")
                p.terminate()
                p.wait(timeout=5)
        print("指揮中心已關閉。")


if __name__ == "__main__":
    main()
