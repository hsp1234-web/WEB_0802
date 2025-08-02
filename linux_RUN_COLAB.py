# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 Colab 指揮中心 V24 (API 驅動版)                      ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 架構：純前端，透過 API 輪詢後端狀態，動態渲染儀表板。            ║
# ║   - 職責：準備環境、啟動後端服務、監控狀態、觸發優雅關機。           ║
# ║   - 版本：0.1.6 (客製化版本)                                         ║
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

#@title 🚀 V24 鳳凰之心指揮中心 (WEB_0802 客製版) { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 程式碼與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤，以及專案資料夾。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "0.1.6" #@param {type:"string"}
#@markdown **專案資料夾名稱 (PROJECT_FOLDER_NAME)**
# --- 說明：從環境變數 PHOENIX_PROJECT_FOLDER 讀取，若未設定則使用 Colab 表單預設值。
PROJECT_FOLDER_NAME = os.getenv("PHOENIX_PROJECT_FOLDER", "WEB_0802") #@param {type:"string"}
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
# --- 說明：從環境變數 PHOENIX_FAST_TEST_MODE 讀取，若未設定則使用 Colab 表單預設值。
_fast_test_mode_str = os.getenv("PHOENIX_FAST_TEST_MODE", "False")
FAST_TEST_MODE = _fast_test_mode_str.lower() in ('true', '1', 't') #@param {type:"boolean"}

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
    # 注意：這裡我們參考 requirements.txt，而不是 requirements-core.txt，以符合專案結構
    requirements_path = project_path / "requirements.txt"
    if not requirements_path.exists():
        update_status(log=f"⚠️ 找不到依賴檔案: {requirements_path}，跳過安裝。")
        return

    # 1. 讀取並解析 requirements 檔案
    update_status(log=f"正在讀取依賴清單: {requirements_path}")
    try:
        with open(requirements_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        update_status(log=f"⚠️ 找不到依賴檔案: {requirements_path}，跳過安裝。")
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

    update_status(log=f"發現 {len(packages_to_install)} 個依賴需要安裝。")

    # 2. 逐一套件安裝與檢查
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for i, package_spec in enumerate(packages_to_install):
            task_header = f"[{i+1}/{len(packages_to_install)}] {package_spec}"
            update_status(task=f"安裝依賴: {package_spec}", log=f"--- {task_header} ---")

            # 2.1 估算套件大小
            update_status(log="[檢查] 正在從 PyPI 估算預計安裝大小...")
            estimated_size_bytes = get_package_size(package_spec, client)

            if estimated_size_bytes == 0:
                update_status(log=f"⚠️ [警告] 無法估算套件 '{package_spec}' 的大小。將跳過空間檢查直接嘗試安裝。")
                required_space_bytes = 10 * 1024 * 1024 # 假設至少需要 10MB
            else:
                required_space_bytes = int(estimated_size_bytes * 1.2) # 20% 緩衝

            estimated_size_mb = estimated_size_bytes / (1024**2)
            required_size_mb = required_space_bytes / (1024**2)

            if estimated_size_bytes > 0:
                 update_status(log=f"[檢查] 預估大小: {estimated_size_mb:.2f} MB。要求可用空間: {required_size_mb:.2f} MB。")

            # 2.2 檢查可用磁碟空間
            free_space_bytes = shutil.disk_usage('/')[2]
            free_space_mb = free_space_bytes / (1024**2)
            update_status(log=f"[檢查] 目前可用磁碟空間: {free_space_mb:.2f} MB。")

            if free_space_bytes < required_space_bytes:
                error_msg = f"空間不足以安裝 '{package_spec}'。需要 {required_size_mb:.2f} MB，僅剩 {free_space_mb:.2f} MB。"
                update_status(log=f"❌ [錯誤] {error_msg}")
                raise RuntimeError(f"安裝中止: {error_msg}")

            update_status(log=f"✅ [檢查] 空間充足，準備開始安裝。")

            # 2.3 執行安裝命令
            start_time = time.monotonic()
            command = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--upgrade", package_spec]
            update_status(log=f"[執行] {' '.join(command)}")

            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, check=True, encoding='utf-8'
                )
                duration = time.monotonic() - start_time
                update_status(log=f"✅ {task_header} 安裝成功，耗時 {duration:.2f} 秒。")

            except subprocess.CalledProcessError as e:
                error_details = e.stderr or e.stdout
                error_msg = f"安裝套件 '{package_spec}' 時發生錯誤。"
                update_status(log=f"❌ [錯誤] {error_msg}")
                update_status(log=f"--- pip 輸出 ---\n{error_details}\n--- pip 輸出結束 ---")
                raise RuntimeError(f"{error_msg} 請檢查日誌以獲取詳細資訊。")

    update_status(log="✅ 所有依賴均已成功安裝。")


def background_worker():
    """在背景執行緒中處理所有耗時任務：準備環境並啟動後端服務。"""
    project_path = None
    try:
        base_path = Path(os.getenv("PHOENIX_CONTENT_ROOT", "/content"))
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

        # --- 步驟 2: 安裝依賴 ---
        # 將原本在步驟3的依賴安裝移到這裡，更符合邏輯流程
        install_core_dependencies(project_path)

        # --- 步驟 3: 執行測試 ---
        update_status(task="執行自動化測試", log="正在啟動 Pytest...")
        pytest_command = [sys.executable, "-m", "pytest"]
        pytest_process = subprocess.run(
            pytest_command,
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        if pytest_process.returncode == 0:
            update_status(log="✅ 自動化測試全部通過。")
        else:
            update_status(log=f"⚠️ 自動化測試出現失敗或錯誤。")
            # 即使測試失敗，我們也顯示輸出並繼續，讓使用者判斷問題
            test_output = pytest_process.stdout or pytest_process.stderr
            update_status(log=f"--- Pytest 輸出 ---\n{test_output}\n--- Pytest 輸出結束 ---")


        # --- 步驟 4: 啟動主應用程式 (linux_RUN.py) ---
        update_status(task="啟動主應用程式")
        launch_script_path = project_path / "linux_RUN.py"
        if not launch_script_path.exists():
            raise FileNotFoundError(f"找不到主應用程式啟動腳本: {launch_script_path}")

        command = [sys.executable, str(launch_script_path)]

        update_status(log=f"🚀 正在使用指令啟動主應用程式: {' '.join(command)}")
        # 使用 Popen 以非阻塞方式執行
        process = subprocess.Popen(
            command,
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        with status_lock:
            shared_status["launch_process"] = process

        update_status(log=f"✅ 主應用程式已在背景啟動 (PID: {process.pid})。")
        update_status(task="應用程式運行中")

    except Exception as e:
        error_message = f"❌ 背景任務發生致命錯誤: {e}"
        update_status(task="背景任務失敗", log=error_message)
        with status_lock:
            shared_status["worker_error"] = str(e)
    finally:
        with status_lock:
            shared_status["worker_finished"] = True
            if "launch_process" not in shared_status or not shared_status["launch_process"]:
                update_status(task="應用程式啟動失敗")

def render_dashboard_html():
    """生成包含動態更新邏輯的儀表板 HTML 骨架"""
    # 此函數保持不變，因為它只負責渲染，不涉及邏輯
    refresh_interval_ms = int(REFRESH_RATE_SECONDS * 1000)

    css = """
    <style>
        body { background-color: #1a1a1a; color: #e0e0e0; font-family: 'Noto Sans TC', 'Fira Code', monospace; }
        .container { padding: 1em; }
        .panel { border: 1px solid #444; margin-bottom: 1em; }
        .title { font-weight: bold; padding: 0.5em; border-bottom: 1px solid #444; background-color: #2a2a2a;}
        .content { padding: 0.5em; }
        .grid { display: grid; grid-template-columns: 1fr 2fr; gap: 1em; }
        .log-container { height: 400px; overflow-y: scroll; background-color: #222; padding: 0.5em; border-radius: 4px; }
        .log-entry { margin-bottom: 5px; white-space: pre-wrap; word-break: break-all; }
        .footer { text-align: center; padding-top: 1em; border-top: 1px solid #444; font-size: 0.8em; color: #888;}
        table { width: 100%;}
        .copy-button { margin-top: 10px; padding: 8px 15px; font-size: 1em; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }
    </style>
    """

    html_body = """
    <div class="container">
        <div class="grid">
            <div>
                <div class="panel">
                    <div class="title">系統狀態</div>
                    <div class="content" id="status-content">等待回報...</div>
                </div>
            </div>
            <div class="panel">
                <div class="title">程序日誌</div>
                <div class="content log-container" id="log-container">等待日誌...</div>
            </div>
        </div>
        <div class="footer" id="footer-status">指揮中心前端任務: 初始化中...</div>
        <div style="text-align: center; margin-top: 1em;">
            <button class="copy-button" onclick="copyLogsToClipboard()">📋 複製日誌</button>
        </div>
    </div>
    """

    javascript = f"""
    <script type="text/javascript">
        const logContainer = document.getElementById('log-container');
        const statusContent = document.getElementById('status-content');
        const footerStatus = document.getElementById('footer-status');

        function copyLogsToClipboard() {{
            const logs = logContainer.innerText;
            navigator.clipboard.writeText(logs).then(() => {{
                alert('日誌已複製到剪貼簿！');
            }}, (err) => {{
                alert('複製失敗: ' + err);
            }});
        }}

        function updateDashboard() {{
            // 在這個版本中，我們直接從 Python 端獲取狀態，而不是透過 API
            // 因此，主要更新將由 Python 的 display(HTML(...)) 觸發
            // 這個 JS 函數可以保留，以備將來需要前端主動輪詢時使用
        }}

        // 這個函數將由 Python 呼叫以更新前端
        window.updateFrontend = function(status) {{
            // 更新狀態面板
            let statusHtml = `<table>`;
            statusHtml += `<tr><td>當前任務</td><td>${{status.current_task || 'N/A'}}</td></tr>`;
            if (status.error) {{
                statusHtml += `<tr><td>錯誤</td><td style="color: #ff5370;">${{status.error}}</td></tr>`;
            }}
            statusHtml += `</table>`;
            statusContent.innerHTML = statusHtml;

            // 更新日誌
            let logHtml = '';
            if (status.logs && status.logs.length > 0) {{
                logHtml = status.logs.join('<br>');
            }}
            logContainer.innerHTML = logHtml;
            logContainer.scrollTop = logContainer.scrollHeight; // 自動滾動到底部

            // 更新頁腳
            footerStatus.textContent = `最後更新: ${{new Date().toLocaleTimeString()}}`;
        }};

        // 立即執行一次，然後設定定時器
        // setInterval(updateDashboard, {REFRESH_RATE_SECONDS * 1000});
    </script>
    """
    return css + html_body + javascript

def main_loop():
    """主迴圈，負責更新儀表板和監控背景任務"""
    start_time = time.time()
    display(HTML(render_dashboard_html()))

    while not shared_status.get('worker_finished', False):
        # 從 Python 更新前端
        with status_lock:
            # 建立一個狀態副本以避免執行緒問題
            current_status = dict(shared_status)

        # 使用 JavascriptChannel 更新前端
        js_command = f"window.updateFrontend({json.dumps(current_status)})"
        if IS_COLAB:
            colab_output.eval_js(js_command)
        else:
            # 在本地模式下，我們只打印狀態到控制台
            # print(f"[本地更新] {current_status['current_task']}")
            pass # 避免洗版

        time.sleep(REFRESH_RATE_SECONDS)

    # 背景工作完成後，做最後一次更新
    with status_lock:
        final_status = dict(shared_status)
    js_command = f"window.updateFrontend({json.dumps(final_status)})"
    if IS_COLAB:
        colab_output.eval_js(js_command)

    if final_status.get("worker_error"):
        update_status(log=f"❌ 工作執行緒因錯誤而終止: {final_status['worker_error']}")
    else:
        update_status(log="✅ 所有背景任務已完成。")

    # 顯示最終日誌
    with status_lock:
        final_status_for_print = dict(shared_status)
    print("\n--- 最終日誌 ---")
    for log in final_status_for_print['logs']:
        print(log)
    print("----------------")


def main():
    if IS_COLAB:
        colab_output.clear(wait=True)

    update_status(log="指揮中心 V24 (WEB_0802 客製版) 啟動。")

    # 啟動背景工作執行緒
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()

    try:
        main_loop()

        # 等待背景主應用程式結束 (如果它被啟動了)
        with status_lock:
            app_process = shared_status.get("launch_process")

        if app_process:
            update_status(log="主應用程式正在運行。您可以隨時手動中斷此儲存格以將其關閉。")
            # 等待程序結束，或直到使用者中斷
            app_process.wait()
            update_status(log=f"主應用程式已終止，返回碼: {app_process.returncode}")

    except KeyboardInterrupt:
        print("\n🛑 偵測到手動中斷 (Ctrl+C)。正在嘗試優雅關機...")
        with status_lock:
            app_process = shared_status.get("launch_process")

        if app_process and app_process.poll() is None:
            update_status(log="正在終止背景主應用程式...")
            app_process.terminate()
            try:
                app_process.wait(timeout=5)
                update_status(log="✅ 背景應用程式已關閉。")
            except subprocess.TimeoutExpired:
                update_status(log="⚠️ 關閉超時，強制終止。")
                app_process.kill()
        else:
            update_status(log="背景應用程式未在運行或已關閉。")

    except Exception as e:
        update_status(log=f"💥 主迴圈發生未預期的錯誤: {e}")

    finally:
        update_status(log="🚀 Colab 指揮中心腳本執行完畢。")
        # 確保工作執行緒已結束
        if worker_thread.is_alive():
            worker_thread.join(timeout=2)


if __name__ == "__main__":
    main()
