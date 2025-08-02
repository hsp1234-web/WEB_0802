# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 Colab 指揮中心 V24 (API 驅動版)                      ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 架構：純前端，透過 API 輪詢後端狀態，動態渲染儀表板。            ║
# ║   - 職責：準備環境、啟動後端服務、監控狀態、觸發優雅關機。           ║
# ║   - 版本：0.1.0                                                      ║
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
from src.phoenix_core.kernel.package_utils import get_package_size

# --- 環境相容性處理 ---
IS_COLAB = 'google.colab' in sys.modules

try:
    import yaml
    import httpx
    if IS_COLAB:
        from google.colab import output as colab_output
    else:
        # 在本地環境中，建立一個模擬的 colab_output 物件
        class MockColabOutput:
            def serve_kernel_port_as_window(self, port, anchor_text=""):
                print(f"[本地模式] Colab 'serve_kernel_port_as_window' 被呼叫於 port {port}")
            def clear_output(self, wait=False):
                # os.system('cls' if os.name == 'nt' else 'clear')
                pass # 在 E2E 測試中，我們不希望清除輸出
        colab_output = MockColabOutput()

except ImportError:
    print("正在安裝指揮中心核心依賴 (PyYAML, httpx)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyyaml", "httpx"])
    import yaml
    import httpx
    # 重新定義模擬物件
    class MockColabOutput:
        def serve_kernel_port_as_window(self, port, anchor_text=""):
            print(f"[本地模式] Colab 'serve_kernel_port_as_window' 被呼叫於 port {port}")
        def clear_output(self, wait=False):
            pass
    colab_output = MockColabOutput()

#@title 🚀 V24 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 程式碼與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤，以及專案資料夾。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/0721_web" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "main" #@param {type:"string"}
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

# --- 共享狀態 ---
shared_status = {
    "current_task": "初始化中...",
    "logs": deque(maxlen=LOG_DISPLAY_LINES),
    "db_status": None,
    "worker_finished": False,
    "worker_error": None,
    "launch_process": None,
    "project_path": None,
}
status_lock = threading.Lock()

def update_status(task=None, log=None):
    """安全地更新共享狀態"""
    with status_lock:
        if task is not None:
            shared_status["current_task"] = task
        if log is not None:
            shared_status["logs"].append(f"[{datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}] {log}")

def install_core_dependencies(project_path: Path):
    """
    安全地安裝核心依賴，採用逐一套件安裝並在安裝前進行動態資源檢查。
    """
    update_status(task="安裝核心依賴", log="正在準備安全安裝程序...")
    requirements_path = project_path / "requirements-core.txt"
    if not requirements_path.exists():
        update_status(log=f"⚠️ 找不到核心依賴檔案: {requirements_path}，跳過安裝。")
        return

    # 1. 讀取並解析 requirements 檔案
    update_status(log=f"正在讀取依賴清單: {requirements_path}")
    try:
        with open(requirements_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        update_status(log=f"⚠️ 找不到核心依賴檔案: {requirements_path}，跳過安裝。")
        return


    packages_to_install = []
    for line in lines:
        # 去除行內註解 (從 '#' 開始的部分)
        line_content = line.split('#')[0].strip()
        # 只有在處理後還有內容時才加入列表
        if line_content:
            packages_to_install.append(line_content)

    if not packages_to_install:
        update_status(log="✅ 依賴清單為空，無需安裝。")
        return

    update_status(log=f"發現 {len(packages_to_install)} 個核心依賴需要安裝。")

    # 2. 逐一套件安裝與檢查
    # 使用 httpx.Client 提高效率，避免為每個請求建立新連線
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        for i, package_spec in enumerate(packages_to_install):
            task_header = f"[{i+1}/{len(packages_to_install)}] {package_spec}"
            update_status(task=f"安裝依賴: {package_spec}", log=f"--- {task_header} ---")

            # 2.1 估算套件大小
            update_status(log="[檢查] 正在從 PyPI 估算預計安裝大小...")
            estimated_size_bytes = get_package_size(package_spec, client)

            if estimated_size_bytes == 0:
                update_status(log=f"⚠️ [警告] 無法估算套件 '{package_spec}' 的大小。將跳過空間檢查直接嘗試安裝。")
                # 雖然我們無法檢查，但還是要確保至少有基礎的空間
                required_space_bytes = 10 * 1024 * 1024 # 假設至少需要 10MB
            else:
                # 增加 20% 的安全緩衝，以應對解壓縮後的體積和依賴
                required_space_bytes = int(estimated_size_bytes * 1.2)

            estimated_size_mb = estimated_size_bytes / (1024**2)
            required_size_mb = required_space_bytes / (1024**2)

            if estimated_size_bytes > 0:
                 update_status(log=f"[檢查] 預估大小: {estimated_size_mb:.2f} MB。要求可用空間 (含緩衝): {required_size_mb:.2f} MB。")

            # 2.2 檢查可用磁碟空間
            free_space_bytes = shutil.disk_usage('/')[2]
            free_space_mb = free_space_bytes / (1024**2)

            update_status(log=f"[檢查] 目前可用磁碟空間: {free_space_mb:.2f} MB。")

            if free_space_bytes < required_space_bytes:
                error_msg = (
                    f"可用磁碟空間不足以安裝 '{package_spec}'。 "
                    f"需要 {required_size_mb:.2f} MB，但僅剩 {free_space_mb:.2f} MB。"
                )
                update_status(log=f"❌ [錯誤] {error_msg}")
                raise RuntimeError(f"安裝中止: {error_msg}")

            update_status(log=f"✅ [檢查] 空間充足，準備開始安裝。")

            # 2.3 執行安裝命令
            start_time = time.monotonic()
            # 使用 --no-cache-dir 確保在資源受限環境下不因快取佔用過多空間
            command = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--upgrade", package_spec]
            update_status(log=f"[執行] {' '.join(command)}")

            try:
                # 使用 subprocess.run 等待命令完成，更簡潔
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True,  # 如果返回非零，則引發 CalledProcessError
                    encoding='utf-8'
                )
                duration = time.monotonic() - start_time
                # 成功時，只記錄關鍵訊息，避免日誌被 pip 輸出淹沒
                update_status(log=f"✅ {task_header} 安裝成功，耗時 {duration:.2f} 秒。")

            except subprocess.CalledProcessError as e:
                # 安裝失敗時，提供詳細的錯誤輸出
                error_details = e.stderr or e.stdout
                error_msg = f"安裝套件 '{package_spec}' 時發生錯誤。"
                update_status(log=f"❌ [錯誤] {error_msg}")
                update_status(log=f"--- pip 輸出 ---\n{error_details}\n--- pip 輸出結束 ---")
                raise RuntimeError(f"{error_msg} 請檢查日誌以獲取詳細資訊。")

    update_status(log="✅ 所有核心依賴均已成功安裝。")


def background_worker():
    """在背景執行緒中處理所有耗時任務：準備環境並啟動後端服務。"""
    project_path = None
    try:
        base_path = Path("/content")
        project_path = base_path / PROJECT_FOLDER_NAME
        with status_lock:
            shared_status["project_path"] = project_path

        # --- 步驟 1: 準備專案環境 ---
        update_status(task="準備專案環境", log="檢查專案資料夾...")
        if FORCE_REPO_REFRESH and project_path.exists():
            update_status(log="偵測到強制刷新，正在刪除舊的專案資料夾...")
            shutil.rmtree(project_path)
            update_status(log="✅ 舊資料夾已刪除。")

        if not project_path.exists():
            update_status(log=f"正在從 {REPOSITORY_URL} (分支/標籤: {TARGET_BRANCH_OR_TAG}) 下載程式碼...")
            process = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", TARGET_BRANCH_OR_TAG, REPOSITORY_URL, str(project_path)],
                capture_output=True, text=True, encoding='utf-8'
            )
            if process.returncode != 0:
                raise RuntimeError(f"Git clone 失敗: {process.stderr}")
            update_status(log="✅ 程式碼下載成功。")
        else:
            update_status(log="專案資料夾已存在，跳過下載。")

        # --- 步驟 2: 生成設定檔 ---
        update_status(task="生成專案設定檔", log="正在根據 Colab 表單生成 config.json...")
        log_level = "INFO"
        if SHOW_LOG_LEVEL_PERF: log_level = "PERF"
        if SHOW_LOG_LEVEL_CMD: log_level = "CMD"
        if SHOW_LOG_LEVEL_SHELL: log_level = "SHELL"
        if SHOW_LOG_LEVEL_INFO: log_level = "DEBUG"

        config_data = {
            "log_level": log_level,
            "REFRESH_RATE_SECONDS": REFRESH_RATE_SECONDS,
            "TIMEZONE": TIMEZONE,
        }
        config_file = project_path / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        update_status(log=f"✅ Colab 設定檔 (config.json) 已生成，日誌等級設為 {log_level}。")

        # --- 步驟 3: 安裝核心依賴 ---
        install_core_dependencies(project_path)

        # --- 步驟 4: 啟動後端 API 服務 ---
        update_status(task="啟動後端 API 服務")
        launch_script_path = project_path / "scripts" / "launch.py"
        if not launch_script_path.exists():
            raise FileNotFoundError(f"找不到後端啟動腳本: {launch_script_path}")

        # 準備命令，包含設定檔參數
        command = [
            sys.executable,
            str(launch_script_path),
            "--config",
            str(config_file)
        ]

        update_status(log=f"🚀 正在使用指令啟動後端服務: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        with status_lock:
            shared_status["launch_process"] = process

        update_status(log=f"✅ 後端服務已在背景啟動 (PID: {process.pid})。儀表板將開始輪詢狀態。")
        update_status(task="後端服務運行中")

    except Exception as e:
        error_message = f"❌ 背景任務發生致命錯誤: {e}"
        update_status(task="背景任務失敗", log=error_message)
        with status_lock:
            shared_status["worker_error"] = str(e)
    finally:
        with status_lock:
            shared_status["worker_finished"] = True
            # 如果 launch_process 沒有被設定，說明啟動失敗
            if "launch_process" not in shared_status or not shared_status["launch_process"]:
                update_status(task="後端啟動失敗")

def render_dashboard_html():
    """生成包含動態更新邏輯的儀表板 HTML 骨架"""
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

    javascript = """
    <script type="text/javascript">
        let currentStatusData = {{}};
        const statusMap = {{
            "running": "🟢 運行中", "pending": "🟡 等待中",
            "installing": "🛠️ 安裝中", "starting": "🚀 啟動中",
            "failed": "🔴 失敗", "unknown": "❓ 未知"
        }};
        const apiUrl = 'http://localhost:8088/api/v1/status';

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
    """.format(refresh_interval_ms=refresh_interval_ms)
    return css + html_body + javascript

async def check_backend_ready(url: str, timeout: int = 2) -> bool:
    """非同步檢查後端服務是否已就緒。"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False

async def serve_proxy_url_with_retry(health_check_url: str, port: int, retries: int, delay: int):
    """
    帶重試邏輯，檢查後端並顯示 Colab 代理 URL。
    """
    import asyncio
    update_status(log=f"🔗 [URL 服務] 已啟動，開始監控後端 API 健康狀態 ({health_check_url})...")
    for attempt in range(retries):
        if await check_backend_ready(health_check_url):
            update_status(log=f"✅ [URL 服務] 後端 API 已就緒，正在生成代理 URL...")
            try:
                # 使用 `colab_output.serve_kernel_port_as_window` 提供更乾淨的體驗
                colab_output.serve_kernel_port_as_window(port, anchor_text="在新分頁中開啟主控台")
                update_status(log="✅ [URL 服務] Colab 代理連結已成功顯示。")
            except Exception as e:
                update_status(log=f"❌ [URL 服務] 呼叫 serve_kernel_port_as_window 失敗: {e}")
            return

        if attempt < retries - 1:
            update_status(log=f"🟡 [URL 服務] 後端尚未就緒 (嘗試 {attempt + 1}/{retries})，將在 {delay} 秒後重試...")
            await asyncio.sleep(delay)

    update_status(log=f"❌ [URL 服務] 在 {retries} 次嘗試後，後端 API 仍未回應。URL 無法生成。")


def main():
    update_status(log="指揮中心 V24 API-驅動版啟動。")

    if IS_COLAB:
        clear_output(wait=True)
        display(HTML(render_dashboard_html()))
    else:
        print("偵測到本地模式，將不會渲染 HTML 儀表板。")

    # 啟動背景工作執行緒，負責啟動後端
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()

    # 此處不再需要 URL 服務執行緒，因為新的架構中，
    # Colab URL 的生成與主應用無關，且狀態 API 已足夠。
    # 我們簡化流程，專注於監控後端程序。

    try:
        # 等待背景工作執行緒完成其啟動任務
        worker_thread.join()

        with status_lock:
            launch_process_local = shared_status.get("launch_process")
            worker_error = shared_status.get("worker_error")

        if worker_error:
            raise RuntimeError(f"背景工作執行緒啟動失敗: {worker_error}")
        if not launch_process_local:
            raise RuntimeError("背景工作執行緒結束，但未能成功啟動後端服務。")

        update_status(log="[前端] 後端程序已啟動。前端進入監控模式。可隨時手動中斷此儲存格來觸發後端優雅關機。")

        # 等待後端程序自然結束
        # launch.py 現在是一個服務，理論上會一直運行直到被告知關閉
        # .wait() 會阻塞直到程序終止
        exit_code = launch_process_local.wait()
        update_status(log=f"[前端] 後端程序已終止，返回碼: {exit_code}。前端任務完成。")

    except KeyboardInterrupt:
        print("\n" + "="*80)
        print("🛑 偵測到手動中斷，正在向後端 API 發送優雅關閉信號...")
        print("="*80)
        try:
            # 不再檢查 launch_process，直接嘗試呼叫 API
            shutdown_url = 'http://localhost:8088/api/v1/shutdown'
            print(f"正在向 {shutdown_url} 發送 POST 請求...")
            # 使用 httpx 發送請求
            with httpx.Client() as client:
                response = client.post(shutdown_url, timeout=10)

            if response.status_code == 200:
                print("✅ 成功發送關閉信號。後端將在背景完成資料庫儲存。")
                print("   請等待幾秒鐘，然後在下一個儲存格執行「報告生成器」。")
            else:
                print(f"⚠️ 發送關閉信號可能失敗，後端回應: {response.status_code} - {response.text}")
                print("   將嘗試強制終止後端程序...")
                with status_lock:
                    launch_process_local = shared_status.get("launch_process")
                if launch_process_local:
                    launch_process_local.terminate()
        except httpx.RequestError as req_exc:
            print(f"❌ 發送關閉信號時發生網路錯誤: {req_exc}")
            print("   可能是後端服務已提前崩潰。建議檢查後端日誌。")
        except Exception as shutdown_exc:
            print(f"❌ 在嘗試優雅關閉後端時發生未預期的錯誤: {shutdown_exc}")
            print("   狀態可能未正確儲存。")

def run_main():
    try:
        main()
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, KeyboardInterrupt):
            print("\n🛑 操作已被使用者手動中斷。")
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}")
    finally:
        pass


if __name__ == "__main__":
    run_main()
