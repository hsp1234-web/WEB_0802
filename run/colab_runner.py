# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 鳳凰之心 - V35 Colab 指揮中心 (穩定版)               ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - V35 更新日誌:                                                      ║
# ║   - 核心架構向使用者提供的 V19 穩定版腳本看齊。                    ║
# ║   - 採用多執行緒模型，非阻塞式 UI，提升啟動速度與穩定性。          ║
# ║   - 改用 JS `fetch` 定時請求後端 API (`/api/v1/status/dashboard`)  ║
# ║     來更新介面，取代原有的 Python-push-JS 模式。                   ║
# ║   - 修正 `git clone` 指令，使用 `--depth 1` 淺層複製，解決下載問題。 ║
# ║   - 介面風格與 V19 保持一致。                                      ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 💎 鳳凰之心指揮中心 V35 { vertical-output: true, display-mode: "form" }
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
# 🚀 核心邏輯
# ==============================================================================
import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import json
from IPython.display import display, HTML, clear_output
import threading
from collections import deque
import html
from datetime import datetime

# --- 共享狀態與日誌 ---
# 使用 deque 作為固定長度的日誌隊列
logs_deque = deque(maxlen=LOG_DISPLAY_LINES)

def log_message(message):
    """將訊息添加到日誌隊列"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    logs_deque.append(f"[{timestamp}] {message}")

def background_worker():
    """在背景執行緒中處理所有耗時的啟動任務"""
    try:
        # --- 步驟 1: 準備專案環境 ---
        log_message("準備專案環境...")
        base_path = Path("/content")
        project_path = base_path / PROJECT_FOLDER_NAME

        if FORCE_REPO_REFRESH and project_path.exists():
            log_message("偵測到強制刷新，正在刪除舊的專案資料夾...")
            shutil.rmtree(project_path)
            log_message("✅ 舊資料夾已刪除。")

        if not project_path.exists():
            log_message(f"正在從 Github 下載程式碼 (分支: {TARGET_BRANCH_OR_TAG})...")
            git_command = [
                "git", "clone",
                "--branch", TARGET_BRANCH_OR_TAG,
                "--depth", "1",
                REPOSITORY_URL,
                str(project_path)
            ]
            process = subprocess.run(git_command, capture_output=True, text=True, check=False)
            if process.returncode != 0:
                raise RuntimeError(f"Git clone 失敗: {process.stderr}")
            log_message("✅ 程式碼下載成功。")
        else:
            log_message("專案資料夾已存在，跳過下載。")

        os.chdir(project_path)
        if str(project_path) not in sys.path:
            sys.path.insert(0, str(project_path))

        # --- 步驟 2: 準備設定檔 ---
        log_message("正在生成後端設定檔...")
        enabled_log_levels = {
            "BATTLE": SHOW_LOG_LEVEL_BATTLE, "SUCCESS": SHOW_LOG_LEVEL_SUCCESS,
            "INFO": SHOW_LOG_LEVEL_INFO, "CMD": SHOW_LOG_LEVEL_CMD,
            "LOG_SHELL": SHOW_LOG_LEVEL_LOG_SHELL, "ERROR": SHOW_LOG_LEVEL_ERROR,
            "CRITICAL": SHOW_LOG_LEVEL_CRITICAL, "PERF": SHOW_LOG_LEVEL_PERF
        }
        config_data = {
            "log_settings": {"levels": enabled_log_levels}
        }
        config_file = project_path / "temp_config_for_runner.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        log_message("✅ 後端設定檔已生成。")

        # 將設定檔路徑寫入環境變數
        os.environ["PHOENIX_CONFIG_PATH"] = str(config_file)

        # --- 步驟 3: 安裝依賴 ---
        log_message("正在安裝後端依賴...")
        requirements_path = "requirements/base.txt"
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", requirements_path], check=True)
        log_message("✅ 後端依賴安裝完成。")

        # --- 步驟 4: 啟動後端服務 ---
        log_message(f"🔥 正在啟動後端服務於埠 {API_PORT}...")
        log_file = open("api_server.log", "w")
        subprocess.Popen([
            sys.executable, "-m", "uvicorn", "src.phoenix_core.main:app",
            "--host", "0.0.0.0", "--port", str(API_PORT)
        ], stdout=log_file, stderr=subprocess.STDOUT, cwd=project_path)
        log_message("✅ 後端服務已在背景啟動。")

    except Exception as e:
        log_message(f"❌ 背景任務發生致命錯誤: {e}")

def render_dashboard_html():
    """生成包含動態更新邏輯的儀表板 HTML"""
    refresh_interval_ms = int(REFRESH_RATE_SECONDS * 1000)

    # 來自 V24 的 CSS，進行了微調以適應 V35 的架構
    css = f"""
    <style>
        body {{ background-color: transparent; color: var(--colab-primary-text-color, #e0e0e0); font-family: 'Noto Sans TC', 'Fira Code', monospace; }}
        .container {{ padding: 1em; }}
        .panel {{ border: 1px solid var(--colab-border-color, #444); margin-bottom: 1em; border-radius: 8px; overflow: hidden; }}
        .title {{ font-weight: bold; padding: 0.5em 1em; border-bottom: 1px solid var(--colab-border-color, #444); background-color: var(--colab-section-header-color, #2a2a2a);}}
        .content {{ padding: 1em; }}
        .grid {{ display: grid; grid-template-columns: 1fr 2fr; gap: 1em; }}
        .log-panel {{ height: {LOG_DISPLAY_LINES * 20}px; overflow-y: auto; background-color: var(--colab-secondary-surface-color, #2d2d2d); font-size: 0.9em; white-space: pre-wrap; word-break: break-all; border-radius: 4px; }}
        .footer {{ text-align: center; padding-top: 1em; border-top: 1px solid #444; font-size: 0.8em; color: #888;}}
        table {{ width: 100%; border-collapse: collapse; }}
        td {{ padding: 4px 8px; }}
        .log-entry {{ margin-bottom: 5px; }}
        .log-level-BATTLE {{ color: #82aaff; }}
        .log-level-SUCCESS {{ color: #c3e88d; }}
        .log-level-ERROR, .log-level-CRITICAL {{ color: #ff5370; }}
        .log-level-INFO {{ color: #89ddff; }}
        .log-level-WARN, .log-level-LOG_SHELL, .log-level-CMD {{ color: #ffcb6b; }}
        #entry-point-panel {{ display: none; grid-column: 1 / -1; text-align: center; padding: 1em; background-color: #2d2d2d; border: 1px solid #50fa7b; border-radius: 8px; }}
        #entry-point-button {{ display: inline-block; padding: 10px 20px; font-size: 1.2em; font-weight: bold; color: #1a1a1a; background-color: #50fa7b; border: none; border-radius: 5px; text-decoration: none; cursor: pointer; }}
        #copy-status-button {{ margin-top: 10px; padding: 8px 15px; font-size: 1em; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }}
    </style>
    """

    # 來自 V24 的 HTML 結構
    html_body = """
    <div class="container">
        <div class="grid">
            <div>
                <div class="panel">
                    <div class="title">📊 微服務狀態</div>
                    <div class="content"><table id="app-status-table"><tbody><tr><td>等待後端回報...</td></tr></tbody></table></div>
                </div>
                <div class="panel">
                    <div class="title">⚙️ 系統資源</div>
                    <div class="content">
                        <table>
                            <tbody>
                                <tr><td>CPU</td><td id="cpu-usage">--%</td></tr>
                                <tr><td>RAM</td><td id="ram-usage">--%</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="panel">
                <div class="title">📜 運行日誌</div>
                <div class="content log-panel" id="log-container">日誌初始化中...</div>
            </div>
        </div>
        <div id="entry-point-panel">
             <a id="entry-point-button" href="#" target="_blank">🚀 進入主控台</a>
             <p style="font-size:0.9em; margin-top: 8px;">主儀表板已就緒，點擊上方按鈕進入操作介面。</p>
        </div>
        <div class="footer" id="footer-status">指揮中心前端任務: 初始化中...</div>
        <div style="text-align: center; margin-top: 1em;">
            <button id="copy-status-button">📋 複製純文字狀態</button>
        </div>
    </div>
    """

    # 融合 V24 和 V35 的 JavaScript
    javascript = f"""
    <script>
        const apiUrl = 'http://localhost:{API_PORT}/api/v1/status/dashboard';
        const logContainer = document.getElementById('log-container');
        const appStatusTable = document.getElementById('app-status-table').querySelector('tbody');
        const cpuUsageTd = document.getElementById('cpu-usage');
        const ramUsageTd = document.getElementById('ram-usage');
        const footerStatus = document.getElementById('footer-status');
        const entryPointPanel = document.getElementById('entry-point-panel');
        const entryPointButton = document.getElementById('entry-point-button');
        const copyStatusButton = document.getElementById('copy-status-button');
        let currentStatusData = {{}};

        const statusMap = {{
            "running": "🟢 運行中", "pending": "🟡 等待中",
            "installing": "🛠️ 安裝中", "starting": "🚀 啟動中",
            "failed": "🔴 失敗", "stopped": "⚪️ 已停止", "unknown": "❓ 未知"
        }};

        function formatStatusForCopy(data) {{
            if (!data || Object.keys(data).length === 0) return "狀態資訊不完整，無法生成報告。";
            let text = `鳳凰之心狀態報告 (即時)\\n`;
            text += `========================\\n`;
            text += `核心階段: ${{data.current_stage || 'N/A'}}\\n`;
            text += `CPU: ${{data.cpu_usage != null ? data.cpu_usage.toFixed(1) : 'N/A'}}%, RAM: ${{data.ram_usage != null ? data.ram_usage.toFixed(1) : 'N/A'}}%\\n\\n`;
            text += `微服務狀態:\\n`;
            if (data.apps_status && Object.keys(data.apps_status).length > 0) {{
                 for (const [name, status] of Object.entries(data.apps_status)) {{
                    text += `- ${{name}}: ${{statusMap[status] || status}}\\n`;
                }}
            }} else {{
                text += `- 尚無服務狀態回報\\n`;
            }}
            text += `\\n最新日誌:\\n`;
            if (data.logs && data.logs.length > 0) {{
                const reversedLogs = [...data.logs].reverse();
                reversedLogs.forEach(log => {{
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
                copyStatusButton.textContent = '✅ 已複製！';
            }} catch (err) {{
                copyStatusButton.textContent = '❌ 複製失敗';
            }}
            document.body.removeChild(textarea);
            setTimeout(() => {{ copyStatusButton.textContent = '📋 複製純文字狀態'; }}, 2000);
        }}

        copyStatusButton.onclick = () => copyToClipboard(formatStatusForCopy(currentStatusData));

        function updateDashboard() {{
            fetch(apiUrl)
                .then(response => {{
                    if (!response.ok) {{
                        footerStatus.textContent = `前端狀態: 後端服務尚未就緒... (HTTP ${{response.status}})`;
                        return;
                    }}
                    return response.json();
                }})
                .then(data => {{
                    if (!data) return;
                    currentStatusData = data;

                    // 更新日誌
                    let logEntries = '';
                    if (data.logs && data.logs.length > 0) {{
                        const reversedLogs = [...data.logs].reverse();
                        reversedLogs.forEach(log => {{
                            const time = new Date(log.timestamp).toLocaleTimeString('en-GB');
                            const level = log.level.toUpperCase();
                            const message = log.message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                            logEntries += `<div class="log-entry"><span class="log-level-${{level}}">[${{time}}] [${{level}}]</span> ${{message}}</div>`;
                        }});
                    }}
                    logContainer.innerHTML = logEntries;
                    if(logContainer.innerHTML) logContainer.scrollTop = logContainer.scrollHeight;

                    // 更新微服務狀態
                    let appRows = '';
                    if (data.apps_status && Object.keys(data.apps_status).length > 0) {{
                        for (const [appName, status] of Object.entries(data.apps_status)) {{
                            const statusText = statusMap[status] || statusMap['unknown'];
                            appRows += `<tr><td>${{appName}}</td><td>${{statusText}}</td></tr>`;
                        }}
                    }} else {{
                        appRows = '<tr><td>等待後端回報...</td></tr>';
                    }}
                    appStatusTable.innerHTML = appRows;

                    // 更新系統資源
                    cpuUsageTd.textContent = data.cpu_usage != null ? `${{data.cpu_usage.toFixed(1)}}%` : '--%';
                    ramUsageTd.textContent = data.ram_usage != null ? `${{data.ram_usage.toFixed(1)}}%` : '--%';

                    // 更新頁腳和主控台入口
                    footerStatus.textContent = `指揮中心後端任務: ${{data.current_stage || '所有服務運行中'}}`;
                    if (data.action_url) {{
                        entryPointPanel.style.display = 'block';
                        entryPointButton.href = data.action_url;
                    }} else {{
                        entryPointPanel.style.display = 'none';
                    }}
                }})
                .catch(error => {{
                    footerStatus.textContent = `前端狀態: 網路錯誤或後端無回應`;
                    currentStatusData = {{ error: error.message }};
                }});
        }}

        setInterval(updateDashboard, {refresh_interval_ms});
        updateDashboard();
    </script>
    """
    return css + html_body + javascript

def main():
    """主執行函數"""
    clear_output(wait=True)

    # 顯示靜態的啟動日誌面板
    log_display_html = f"""
    <style> .startup-log-container {{ padding: 1em; border: 1px solid #444; background-color: #2a2a2a; color: #e0e0e0; font-family: monospace; height: 300px; overflow-y: auto; border-radius: 8px;}} </style>
    <div class="startup-log-container" id="startup-log"></div>
    <script>
        const startupLogContainer = document.getElementById('startup-log');
        let logFetchInterval;
        function fetchStartupLogs() {{
            // 在 JS 中安全地創建日誌內容
            const logs = {json.dumps(list(logs_deque))};
            startupLogContainer.innerHTML = logs.join('<br>');
            startupLogContainer.scrollTop = startupLogContainer.scrollHeight;
        }}
        logFetchInterval = setInterval(fetchStartupLogs, 1000);
    </script>
    """
    display(HTML(log_display_html))

    # 在背景啟動耗時任務
    worker_thread = threading.Thread(target=background_worker)
    worker_thread.start()

    # 等待背景任務完成後端啟動
    worker_thread.join(timeout=180) # 最長等待3分鐘

    # 清理啟動日誌並顯示主儀表板
    clear_output(wait=True)
    if worker_thread.is_alive():
        log_message("❌ 背景任務啟動超時。")

    display(HTML(render_dashboard_html()))

if __name__ == "__main__":
    main()
