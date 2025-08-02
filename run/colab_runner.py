# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 Colab 指揮中心 V29 (功能擴充版)                      ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 架構：Colab UI 負責準備環境、啟動後端，並提供一個               ║
# ║           API 驅動的儀表板來監控狀態。                             ║
# ║ - 版本：0.2.9 (全面測試與功能更新)                                 ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
import os
import sys
import shutil
import subprocess
import threading
import time
import json
from pathlib import Path
from IPython.display import display, HTML, clear_output
import pytz
from datetime import datetime
from collections import deque

# --- 環境相容性處理 ---
IS_COLAB = 'google.colab' in sys.modules

try:
    if IS_COLAB:
        from google.colab import output as colab_output
    else:
        class MockColabOutput:
            def serve_kernel_port_as_window(self, port, anchor_text=""): print(f"[本地模式] Colab 'serve_kernel_port_as_window' 被呼叫於 port {port}")
            def clear_output(self, wait=False): pass
        colab_output = MockColabOutput()
except ImportError:
    class MockColabOutput:
        def serve_kernel_port_as_window(self, port, anchor_text=""): print(f"[本地模式] Colab 'serve_kernel_port_as_window' 被呼叫於 port {port}")
        def clear_output(self, wait=False): pass
    colab_output = MockColabOutput()

# --- Colab 使用者介面參數 ---
#@title 🚀 V27 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### Part 1: 程式碼與環境設定
#@markdown > 設定 Git 倉庫、分支或標籤，以及專案資料夾。
#@markdown ---
#@markdown 後端程式碼倉庫 (REPOSITORY_URL)
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown 後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)
TARGET_BRANCH_OR_TAG = "0.3.0" #@param {type:"string"}
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


# ==============================================================================
# 🚀 核心邏輯
# ==============================================================================

shared_status = {
    "current_task": "初始化中...",
    "logs": deque(maxlen=LOG_DISPLAY_LINES),
    "backend_process": None,
}
status_lock = threading.Lock()

def update_status(task=None, log=None):
    with status_lock:
        if task is not None:
            shared_status["current_task"] = task
        if log is not None:
            log_message = f"[{datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}] {log}"
            shared_status["logs"].append(log_message)
            print(log_message)

def background_worker():
    project_path = None
    try:
        base_path = Path("/content")
        project_path = base_path / PROJECT_FOLDER_NAME

        update_status(task="準備專案環境", log="檢查專案資料夾...")
        if FORCE_REPO_REFRESH and project_path.exists():
            update_status(log=f"偵測到強制刷新，正在刪除舊的專案資料夾: {project_path}...")
            shutil.rmtree(project_path)
            update_status(log="✅ 舊資料夾已刪除。")

        if not project_path.exists():
            update_status(log=f"正在從 {REPOSITORY_URL} (分支/標籤: {TARGET_BRANCH_OR_TAG}) 下載程式碼...")
            process = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", TARGET_BRANCH_OR_TAG, REPOSITORY_URL, str(project_path)],
                capture_output=True, text=True, encoding='utf-8', check=False
            )
            if process.returncode != 0:
                raise RuntimeError(f"Git clone 失敗: {process.stderr}")
            update_status(log="✅ 程式碼下載成功。")
        else:
            update_status(log="專案資料夾已存在，跳過下載。")

        update_status(task="生成專案設定檔", log="正在生成 config.json...")
        config_data = {
            "system_settings": { "timezone": TIMEZONE },
            "log_settings": {
                "levels": {
                    "BATTLE": SHOW_LOG_LEVEL_BATTLE,
                    "SUCCESS": SHOW_LOG_LEVEL_SUCCESS,
                    "INFO": SHOW_LOG_LEVEL_INFO,
                    "CMD": SHOW_LOG_LEVEL_CMD,
                    "SHELL": SHOW_LOG_LEVEL_SHELL,
                    "ERROR": SHOW_LOG_LEVEL_ERROR,
                    "CRITICAL": SHOW_LOG_LEVEL_CRITICAL,
                    "PERF": SHOW_LOG_LEVEL_PERF
                }
            }
        }
        config_file_path = project_path / "config.json"
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        update_status(log=f"✅ config.json 已生成於 {config_file_path}")

        update_status(task="啟動後端 API 服務", log="準備啟動後端服務...")
        launch_script_path = project_path / "scripts" / "start_api_service.py"
        if not launch_script_path.exists():
            raise FileNotFoundError(f"找不到後端啟動腳本: {launch_script_path}")

        command = [
            sys.executable,
            str(launch_script_path),
            "--config", str(config_file_path)
        ]

        update_status(log=f"🚀 正在使用指令啟動後端服務: {' '.join(command)}")
        log_file = open('api_server.log', 'w')
        process = subprocess.Popen(
            command,
            cwd=project_path,
            stdout=log_file,
            stderr=log_file,
            text=True,
            encoding='utf-8'
        )

        with status_lock:
            shared_status["backend_process"] = process

        update_status(log=f"✅ 後端服務已在背景啟動 (PID: {process.pid})。儀表板將開始輪詢狀態。")
        update_status(task="後端服務運行中")

    except Exception as e:
        error_message = f"❌ 背景任務發生致命錯誤: {e}"
        update_status(task="背景任務失敗", log=error_message)
        import traceback
        traceback.print_exc()

def render_dashboard_html():
    refresh_interval_ms = int(REFRESH_RATE_SECONDS * 1000)
    css = """
    <style>
        body { background-color: #1a1a1a; color: #e0e0e0; font-family: 'Noto Sans TC', 'Fira Code', monospace; }
        .container { padding: 1em; }
        .panel { border: 1px solid #444; margin-bottom: 1em; border-radius: 8px; overflow: hidden; }
        .title { font-weight: bold; padding: 0.5em; border-bottom: 1px solid #444; background-color: #2a2a2a;}
        .content { padding: 0.8em; }
        .grid { display: grid; grid-template-columns: 1fr 2fr; gap: 1em; }
        .log-container { height: 400px; overflow-y: auto; background-color: #222; padding: 0.5em; border-radius: 5px; }
        .log-entry { font-size: 0.9em; white-space: pre-wrap; word-break: break-all; margin-bottom: 5px; }
        .footer { text-align: center; padding-top: 1em; border-top: 1px solid #444; font-size: 0.8em; color: #888;}
        table { width: 100%; border-collapse: collapse; }
        td { padding: 4px 8px; }
        .log-level-SUCCESS { color: #c3e88d; }
        .log-level-ERROR, .log-level-CRITICAL { color: #ff5370; font-weight: bold; }
        .log-level-INFO { color: #89ddff; }
        .log-level-WARNING { color: #ffcb6b; }
        #entry-point-panel { display: none; grid-column: 1 / -1; text-align: center; padding: 1em; background-color: #2d2d2d; border: 1px solid #50fa7b; }
        #entry-point-button { display: inline-block; padding: 10px 20px; font-size: 1.2em; font-weight: bold; color: #1a1a1a; background-color: #50fa7b; border: none; border-radius: 5px; text-decoration: none; cursor: pointer; }
    </style>
    """
    html_body = """
    <div class="container">
        <div class="grid">
            <div>
                <div class="panel">
                    <div class="title">微服務狀態</div>
                    <div class="content"><table id="app-status-table"><tbody><tr><td>等待後端回報...</td></tr></tbody></table></div>
                </div>
                <div class="panel">
                    <div class="title">系統資源</div>
                    <div class="content">
                        <table>
                            <tr><td>CPU</td><td id="cpu-usage">等待中...</td></tr>
                            <tr><td>RAM</td><td id="ram-usage">等待中...</td></tr>
                        </table>
                    </div>
                </div>
            </div>
            <div class="panel">
                <div class="title">後端即時日誌</div>
                <div class="content log-container" id="log-container">等待日誌...</div>
            </div>
        </div>
        <div id="entry-point-panel">
             <a id="entry-point-button" href="#" target="_blank">🚀 進入主控台</a>
             <p style="font-size:0.9em; margin-top: 8px;">主儀表板已就緒，點擊上方按鈕進入操作介面。</p>
        </div>
        <div class="footer" id="footer-status">指揮中心前端任務: 初始化中...</div>
    </div>
    """
    javascript = f"""
    <script type="text/javascript">
        const statusMap = {{ "running": "🟢 運行中", "pending": "🟡 等待中", "installing": "🛠️ 安裝中", "starting": "🚀 啟動中", "failed": "🔴 失敗", "unknown": "❓ 未知" }};
        const dashboardApiUrl = '/api/v1/status/dashboard';
        const perfApiUrl = '/api/v1/status/performance';

        function updateDashboard() {{
            const fetchDashboard = fetch(dashboardApiUrl).then(res => {{ if (!res.ok) throw new Error('儀表板 API 異常'); return res.json(); }});
            const fetchPerf = fetch(perfApiUrl).then(res => {{ if (!res.ok) throw new Error('效能 API 異常'); return res.json(); }});

            Promise.all([fetchDashboard, fetchPerf])
                .then(([dashboardData, perfData]) => {{
                    document.getElementById('cpu-usage').textContent = `${{perfData.cpu_usage.toFixed(1)}}%`;
                    document.getElementById('ram-usage').textContent = `${{perfData.ram_usage.toFixed(1)}}%`;

                    const appStatusTable = document.getElementById('app-status-table').querySelector('tbody');
                    let appRows = '';
                    if (dashboardData.apps_status && Object.keys(dashboardData.apps_status).length > 0) {{
                        for (const [appName, status] of Object.entries(dashboardData.apps_status)) {{
                            const statusText = statusMap[status] || statusMap['unknown'];
                            appRows += `<tr><td>${{appName}}</td><td>${{statusText}}</td></tr>`;
                        }}
                    }} else {{ appRows = '<tr><td>等待後端回報...</td></tr>'; }}
                    appStatusTable.innerHTML = appRows;

                    const logContainer = document.getElementById('log-container');
                    let logEntries = '';
                    if (dashboardData.logs && dashboardData.logs.length > 0) {{
                        const reversedLogs = [...dashboardData.logs].reverse();
                        reversedLogs.forEach(log => {{
                            const time = new Date(log.timestamp).toLocaleTimeString('en-GB');
                            logEntries += `<div class="log-entry"><span class="log-level-${{log.level}}">[${{time}}] [${{log.level}}]</span> ${{log.message}}</div>`;
                        }});
                    }} else {{ logEntries = '沒有符合條件的日誌。'; }}
                    logContainer.innerHTML = logEntries;
                    logContainer.scrollTop = logContainer.scrollHeight;

                    const footer = document.getElementById('footer-status');
                    const entryPointPanel = document.getElementById('entry-point-panel');
                    const entryPointButton = document.getElementById('entry-point-button');
                    if (dashboardData.action_url) {{
                        entryPointPanel.style.display = 'block';
                        entryPointButton.href = dashboardData.action_url;
                        footer.textContent = `指揮中心後端任務: ${{dashboardData.current_stage || '所有服務運行中'}}`;
                    }} else {{
                        entryPointPanel.style.display = 'none';
                        footer.textContent = `指揮中心後端任務: ${{dashboardData.current_stage || '執行中...'}}`;
                    }}
                }})
                .catch(error => {{
                    const footer = document.getElementById('footer-status');
                    footer.textContent = `前端狀態: 🔴 API 請求失敗 - ${{error.message}}`;
                }});
        }}
        setTimeout(() => {{ updateDashboard(); setInterval(updateDashboard, {refresh_interval_ms}); }}, 5000);
    </script>
    """
    return css + html_body + javascript

def main():
    update_status(log="指揮中心 V27 啟動程序開始。")
    if IS_COLAB:
        clear_output(wait=True)
        display(HTML("<h1>🚀 鳳凰之心指揮中心 V27</h1><p>正在準備環境，請稍候... 初始日誌將顯示於此儲存格下方。</p>"))
    else:
        print("偵測到本地模式，將不會渲染 HTML 儀表板。")

    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()

    while shared_status.get("backend_process") is None and worker_thread.is_alive():
        time.sleep(0.5)

    if shared_status.get("backend_process") is None:
        print("❌ 後端服務啟動失敗，請檢查上方日誌。")
        return

    if IS_COLAB:
        clear_output(wait=True)
        display(HTML(render_dashboard_html()))
    else:
        print("後端已啟動，儀表板在本地模式下不顯示。")

    backend_process = shared_status["backend_process"]
    try:
        exit_code = backend_process.wait()
        update_status(log=f"[前端] 後端程序已終止，返回碼: {exit_code}。")
    except KeyboardInterrupt:
        print("\n🛑 偵測到手動中斷，正在終止後端服務...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
            print("✅ 後端服務已成功終止。")
        except subprocess.TimeoutExpired:
            print("⚠️ 終止超時，強制抹除。")
            backend_process.kill()
        print("✅ 前端程序已結束。")

if __name__ == "__main__":
    main()
