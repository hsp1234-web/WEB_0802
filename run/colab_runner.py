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
    """生成儀表板的 HTML 和 JS"""
    refresh_interval_ms = int(REFRESH_RATE_SECONDS * 1000)

    # 注意：所有 CSS 和 JS 中的大括號都需要加倍以進行轉義
    return f"""
    <style>
        body {{ background-color: transparent; color: var(--colab-primary-text-color, #e0e0e0); font-family: 'Noto Sans TC', 'Fira Code', monospace; }}
        .container {{ padding: 1em; }}
        .panel {{ border: 1px solid var(--colab-border-color, #444); margin-bottom: 1em; border-radius: 8px; overflow: hidden;}}
        .title {{ font-weight: bold; padding: 0.5em 1em; border-bottom: 1px solid var(--colab-border-color, #444); background-color: var(--colab-section-header-color, #2a2a2a);}}
        .content {{ padding: 1em; }}
        .grid {{ display: grid; grid-template-columns: 1fr; gap: 1em; md:grid-template-columns: 1fr 2fr; }}
        .log-panel {{ height: {LOG_DISPLAY_LINES * 20}px; overflow-y: auto; background-color: var(--colab-secondary-surface-color, #2d2d2d); font-size: 0.9em; white-space: pre-wrap; word-break: break-all;}}
        .log-entry {{ margin-bottom: 5px; }}
        .log-level-BATTLE {{ color: #82aaff; }}
        .log-level-SUCCESS {{ color: #c3e88d; }}
        .log-level-ERROR, .log-level-CRITICAL {{ color: #ff5370; }}
        .log-level-INFO {{ color: #89ddff; }}
        .log-level-WARN, .log-level-LOG_SHELL, .log-level-CMD {{ color: #ffcb6b; }}
    </style>
    <div class="container">
        <div class="grid">
            <div>
                <div class="panel">
                    <div class="title">📊 系統狀態</div>
                    <div class="content" id="status-container">等待後端回報...</div>
                </div>
            </div>
            <div class="panel">
                <div class="title">📜 運行日誌</div>
                <div class="content log-panel" id="log-container">日誌初始化中...</div>
            </div>
        </div>
    </div>
    <script>
        const apiUrl = 'http://localhost:{API_PORT}/api/v1/status/dashboard';
        const logContainer = document.getElementById('log-container');
        const statusContainer = document.getElementById('status-container');

        function updateDashboard() {{
            fetch(apiUrl)
                .then(response => {{
                    if (!response.ok) {{
                        return; // 後端未就緒，靜默失敗
                    }}
                    return response.json();
                }})
                .then(data => {{
                    if (!data) return;

                    // 更新日誌
                    let logEntries = '';
                    if (data.logs && data.logs.length > 0) {{
                        data.logs.forEach(log => {{
                            const time = new Date(log.timestamp).toLocaleTimeString('en-GB');
                            const level = log.level.toUpperCase();
                            const message = log.message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                            logEntries += `<div class="log-entry"><span class="log-level-${{level}}">[${{time}}] [${{level}}]</span> ${{message}}</div>`;
                        }});
                    }}
                    logContainer.innerHTML = logEntries;
                    logContainer.scrollTop = logContainer.scrollHeight;

                    // 更新狀態
                    let statusHtml = `<div><strong>核心階段:</strong> ${{data.current_stage}}</div>`;
                    if (data.apps_status) {{
                        for (const [appName, status] of Object.entries(data.apps_status)) {{
                            statusHtml += `<div><strong>${{appName}}:</strong> ${{status}}</div>`;
                        }}
                    }}
                    statusContainer.innerHTML = statusHtml;
                }})
                .catch(error => {{
                    // 忽略網路錯誤，因為服務可能正在啟動
                }});
        }}

        // 啟動定時器
        setInterval(updateDashboard, {refresh_interval_ms});
        updateDashboard(); // 立即執行一次
    </script>
    """

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
