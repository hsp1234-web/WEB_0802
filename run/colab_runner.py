# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 鳳凰之心 - V42 Colab 指揮中心 (最佳實踐版)         ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - V42 更新日誌:                                                      ║
# ║   - **採用 uv venv**: 使用 uv 原生指令創建 venv，速度與穩定性最佳。  ║
# ║   - **移除 os.chdir**: 所有路徑均為絕對路徑，規避環境檢測問題。      ║
# ║   - **--python 旗標**: 強制 uv/pip 在指定 venv 中安裝。              ║
# ║   - 恢復完整 UI，此為最終交付版本。                                  ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 💎 鳳凰之心指揮中心 V42 { vertical-output: true, display-mode: "form" }
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
from datetime import datetime

logs_deque = deque(maxlen=LOG_DISPLAY_LINES)

def log_message(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    logs_deque.append(f"[{timestamp}] {message}")

def background_worker():
    try:
        log_message("準備專案環境...")
        base_path = Path(".").resolve()
        project_path = base_path / PROJECT_FOLDER_NAME

        if FORCE_REPO_REFRESH and project_path.exists():
            shutil.rmtree(project_path)
            log_message(f"✅ 舊資料夾已刪除: {project_path}")

        log_message(f"正在從 Github 下載程式碼至 {project_path}...")
        git_command = ["git", "clone", "--branch", "0.5.1", "--depth", "1", REPOSITORY_URL, str(project_path)]
        subprocess.run(git_command, check=True, capture_output=True, text=True)
        log_message("✅ 程式碼下載成功。")

        if str(project_path) not in sys.path:
            sys.path.insert(0, str(project_path))

        venv_path = project_path / ".venv"
        log_message(f"正在使用 'uv venv' 建立虛擬環境於 {venv_path}...")
        # Assuming uv is installed globally in the sandbox
        subprocess.run(["uv", "venv", str(venv_path)], check=True, capture_output=True, text=True)
        log_message("✅ 虛擬環境建立成功。")

        venv_python = (venv_path / "bin" / "python").resolve()

        process_env = os.environ.copy()
        process_env["VIRTUAL_ENV"] = str(venv_path)
        process_env["PATH"] = f"{venv_path / 'bin'}:{process_env.get('PATH', '')}"

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
        log_message(f"✅ 後端設定檔已生成於 {config_file_path}")
        process_env["PHOENIX_CONFIG_PATH"] = str(config_file_path.resolve())

        log_message("正在使用 uv 安裝核心依賴...")
        core_requirements_path = project_path / "requirements/requirements-core.txt"
        # Use the --python flag to be explicit, even though auto-discovery should work.
        uv_install_command = ["uv", "pip", "install", "--python", str(venv_python), "-r", str(core_requirements_path)]

        subprocess.run(uv_install_command, check=True, env=process_env, capture_output=True, text=True)
        log_message("✅ 核心依賴安裝完成。")

        log_message(f"🔥 正在啟動後端核心服務於埠 {API_PORT}...")
        log_file = project_path / "api_server.log"
        uvicorn_command = [str(venv_python), "-m", "uvicorn", "src.phoenix_core.main:app", "--host", "0.0.0.0", "--port", str(API_PORT)]
        subprocess.Popen(uvicorn_command, stdout=open(log_file, "w"), stderr=subprocess.STDOUT, cwd=str(project_path), env=process_env)
        log_message("✅ 後端核心服務已在背景啟動。")

    except Exception as e:
        log_message(f"❌ 背景任務發生致命錯誤: {e}")

def render_dashboard_html():
    refresh_interval_ms = int(REFRESH_RATE_SECONDS * 1000)
    css = f"""
    <style>
        body {{ background-color: transparent; color: var(--colab-primary-text-color, #e0e0e0); font-family: 'Noto Sans TC', 'Fira Code', monospace; }}
        .container {{ padding: 1em; width: 100%; box-sizing: border-box; }}
        .panel {{ border: 1px solid var(--colab-border-color, #444); margin-bottom: 1em; border-radius: 8px; overflow: hidden; }}
        .title {{ font-weight: bold; padding: 0.5em 1em; border-bottom: 1px solid var(--colab-border-color, #444); background-color: var(--colab-section-header-color, #2a2a2a);}}
        .content {{ padding: 1em; }}
        .grid {{ display: grid; grid-template-columns: 1fr; gap: 1em; width: 100%; }}
        @media (min-width: 768px) {{ .grid {{ grid-template-columns: 1fr 2fr; }} }}
        .log-panel {{ height: {LOG_DISPLAY_LINES * 20}px; overflow-y: auto; background-color: var(--colab-secondary-surface-color, #2d2d2d); font-size: 0.9em; white-space: pre-wrap; word-break: break-all; border-radius: 4px; }}
        .footer {{ text-align: center; padding-top: 1em; border-top: 1px solid #444; font-size: 0.8em; color: #888;}}
        table {{ width: 100%; border-collapse: collapse; }}
        td {{ padding: 4px 8px; }}
        .log-entry {{ margin-bottom: 5px; }}
        .log-level-BATTLE {{ color: #82aaff; }} .log-level-SUCCESS {{ color: #c3e88d; }}
        .log-level-ERROR, .log-level-CRITICAL {{ color: #ff5370; }} .log-level-INFO {{ color: #89ddff; }}
        .log-level-WARN, .log-level-LOG_SHELL, .log-level-CMD {{ color: #ffcb6b; }}
        #entry-point-panel {{ display: none; grid-column: 1 / -1; text-align: center; padding: 1em; background-color: #2d2d2d; border: 1px solid #50fa7b; border-radius: 8px; }}
        #entry-point-button, #install-features-button {{ display: inline-block; padding: 10px 20px; font-size: 1.2em; font-weight: bold; color: #1a1a1a; background-color: #50fa7b; border: none; border-radius: 5px; text-decoration: none; cursor: pointer; }}
        #install-features-button {{ background-color: #f1c40f; }}
        #copy-status-button {{ margin-top: 10px; padding: 8px 15px; font-size: 1em; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }}
    </style>
    """
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
                        <table><tbody>
                            <tr><td>CPU</td><td id="cpu-usage">--%</td></tr>
                            <tr><td>RAM</td><td id="ram-usage">--%</td></tr>
                        </tbody></table>
                    </div>
                </div>
                <div class="panel" id="feature-panel">
                    <div class="title">🧩 功能擴充</div>
                    <div class="content">
                        <p>點擊下方按鈕來安裝額外的功能模組。</p>
                        <button id="install-features-button">安裝資料分析模組</button>
                        <p id="install-status" style="font-size:0.9em; margin-top: 8px;"></p>
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
        <div style="text-align: center; margin-top: 1em;"><button id="copy-status-button">📋 複製純文字狀態</button></div>
    </div>
    """
    javascript = f"""
    <script>
        const apiUrl = 'http://localhost:{API_PORT}/api/v1/status/dashboard';
        const wsUrl = `ws://localhost:{API_PORT}/ws/logs`;
        const logContainer = document.getElementById('log-container');
        const appStatusTable = document.getElementById('app-status-table').querySelector('tbody');
        const cpuUsageTd = document.getElementById('cpu-usage');
        const ramUsageTd = document.getElementById('ram-usage');
        const footerStatus = document.getElementById('footer-status');
        const entryPointPanel = document.getElementById('entry-point-panel');
        const entryPointButton = document.getElementById('entry-point-button');
        const copyStatusButton = document.getElementById('copy-status-button');
        const installFeaturesButton = document.getElementById('install-features-button');
        const installStatus = document.getElementById('install-status');
        let currentStatusData = {{}};

        const statusMap = {{ "running": "🟢 運行中", "pending": "🟡 等待中", "installing": "🛠️ 安裝中", "starting": "🚀 啟動中", "failed": "🔴 失敗", "stopped": "⚪️ 已停止", "unknown": "❓ 未知" }};

        function formatStatusForCopy(data) {{
            if (!data || Object.keys(data).length === 0) return "狀態資訊不完整。";
            let text = `鳳凰之心狀態報告\\n========================\\n`;
            text += `核心階段: ${{data.current_stage || 'N/A'}}\\n`;
            text += `CPU: ${{data.cpu_usage != null ? data.cpu_usage.toFixed(1) : 'N/A'}}%, RAM: ${{data.ram_usage != null ? data.ram_usage.toFixed(1) : 'N/A'}}%\\n\\n`;
            text += `微服務狀態:\\n`;
            if (data.apps_status && Object.keys(data.apps_status).length > 0) {{
                 for (const [name, status] of Object.entries(data.apps_status)) {{ text += `- ${{name}}: ${{statusMap[status] || status}}\\n`; }}
            }} else {{ text += `- 尚無服務狀態回報\\n`; }}
            text += `\\n最新日誌:\\n${{logContainer.innerText || logContainer.textContent || ""}}`;
            return text;
        }}

        copyStatusButton.onclick = () => {{
            const text = formatStatusForCopy(currentStatusData);
            navigator.clipboard.writeText(text).then(() => {{
                copyStatusButton.textContent = '✅ 已複製！';
                setTimeout(() => {{ copyStatusButton.textContent = '📋 複製純文字狀態'; }}, 2000);
            }}, () => {{ copyStatusButton.textContent = '❌ 複製失敗'; }});
        }};

        function renderLogs(logs) {{
            let logEntries = '';
            if (logs && logs.length > 0) {{
                logs.forEach(log => {{
                    const time = new Date(log.timestamp).toLocaleTimeString('en-GB');
                    const level = log.level.toUpperCase();
                    const message = (log.message || '').replace(/</g, "&lt;").replace(/>/g, "&gt;");
                    logEntries += `<div class="log-entry"><span class="log-level-${{level}}">[${{time}}] [${{level}}]</span> ${{message}}</div>`;
                }});
            }}
            logContainer.innerHTML += logEntries;
            logContainer.scrollTop = logContainer.scrollHeight;
        }}

        function setupLogWebSocket() {{
            const socket = new WebSocket(wsUrl);
            socket.onopen = () => {{ footerStatus.textContent = "日誌串流已連接"; logContainer.innerHTML = ''; }};
            socket.onmessage = (event) => {{ renderLogs(JSON.parse(event.data)); }};
            socket.onclose = () => {{ footerStatus.textContent = "日誌串流已中斷，3秒後嘗試重連..."; setTimeout(setupLogWebSocket, 3000); }};
            socket.onerror = () => {{ footerStatus.textContent = "日誌串流發生錯誤。"; }};
        }}

        function updateDashboard() {{
            fetch(apiUrl).then(response => {{
                if (!response.ok) {{ console.warn(`Dashboard fetch failed: HTTP ${{response.status}}`); return; }}
                return response.json();
            }}).then(data => {{
                if (!data) return;
                currentStatusData = data;
                let appRows = '';
                if (data.apps_status && Object.keys(data.apps_status).length > 0) {{
                    for (const [appName, status] of Object.entries(data.apps_status)) {{ appRows += `<tr><td>${{appName}}</td><td>${{statusMap[status] || statusMap['unknown']}}</td></tr>`; }}
                }} else {{ appRows = '<tr><td>等待後端回報...</td></tr>'; }}
                appStatusTable.innerHTML = appRows;
                cpuUsageTd.textContent = data.cpu_usage != null ? `${{data.cpu_usage.toFixed(1)}}%` : '--%';
                ramUsageTd.textContent = data.ram_usage != null ? `${{data.ram_usage.toFixed(1)}}%` : '--%';
                if (data.current_stage && !footerStatus.textContent.startsWith("日誌串流")) {{ footerStatus.textContent = `指揮中心後端任務: ${{data.current_stage}}`; }}
                entryPointPanel.style.display = data.action_url ? 'block' : 'none';
                if(data.action_url) entryPointButton.href = data.action_url;
            }}).catch(error => {{ console.error("Dashboard update error:", error); }});
        }}

        installFeaturesButton.onclick = () => {{
            installStatus.textContent = '正在發送安裝指令...';
            installFeaturesButton.disabled = true;
            fetch('/api/v1/system/install-features', {{ method: 'POST' }}).then(response => {{
                if (response.status === 202) {{
                    installStatus.innerHTML = '✅ 指令已接受，後端正在非同步安裝...';
                }} else {{ return response.json().then(data => {{ throw new Error(data.detail || '未知錯誤'); }}); }}
            }}).catch(error => {{
                installStatus.textContent = `❌ 指令失敗: ${{error.message}}`;
                installFeaturesButton.disabled = false;
            }});
        }};

        setInterval(updateDashboard, {refresh_interval_ms});
        updateDashboard();
        setupLogWebSocket();
    </script>
    """
    return css + html_body + javascript

def main():
    clear_output(wait=True)
    log_display_html = f"""
    <div id="startup-log-container" style="white-space: pre-wrap; font-family: monospace;"></div>
    <script>
        const startupLogContainer = document.getElementById('startup-log-container');
        let logFetchInterval;
        function fetchStartupLogs() {{
            const logs = {json.dumps(list(logs_deque))};
            startupLogContainer.innerHTML = logs.join('<br>');
            startupLogContainer.scrollTop = startupLogContainer.scrollHeight;
        }}
        logFetchInterval = setInterval(fetchStartupLogs, 1000);
    </script>
    """
    display(HTML(log_display_html))
    worker_thread = threading.Thread(target=background_worker)
    worker_thread.start()
    worker_thread.join(timeout=300)
    clear_output(wait=True)
    if worker_thread.is_alive():
        log_message("❌ 背景任務啟動超時。")

    final_html = render_dashboard_html()
    display(HTML(final_html))
    log_message("✅ 指揮中心前端渲染完畢。")

if __name__ == "__main__":
    main()
