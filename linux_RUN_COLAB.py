# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║           🚀 Colab 指揮中心 V25 (uv, 簡化流程版)                   ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 架構: 前端 UI + 背景日誌驅動更新                                 ║
# ║   - 依賴: 自動偵測並安裝 uv，使用 uv 高速安裝                      ║
# ║   - 流程: 簡化為線性執行流程，日誌直接回傳至介面                   ║
# ║   - 版本: 0.2.0                                                      ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import json
from IPython.display import display, HTML, clear_output
import pytz
from datetime import datetime
import threading
from collections import deque

# --- 環境相容性處理 ---
IS_COLAB = 'google.colab' in sys.modules

if IS_COLAB:
    from google.colab import output as colab_output
else:
    # 在本地環境中，建立一個模擬的 colab_output 物件
    class MockColabOutput:
        def eval_js(self, js_code):
            # print(f"[本地模式] JS call: {js_code[:80]}...") # 用於除錯
            pass
        def clear_output(self, wait=False):
            os.system('cls' if os.name == 'nt' else 'clear')
    colab_output = MockColabOutput()

#@title 🚀 V25 鳳凰之心指揮中心 (uv, 簡化流程版) { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 程式碼與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤，以及專案資料夾。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "0.1.6" #@param {type:"string"}
#@markdown **專案資料夾名稱 (PROJECT_FOLDER_NAME)**
PROJECT_FOLDER_NAME = "WEB_0802" #@param {type:"string"}
#@markdown **強制刷新後端程式碼 (FORCE_REPO_REFRESH)**
FORCE_REPO_REFRESH = True #@param {type:"boolean"}

#@markdown ---
#@markdown ### **Part 2: 應用程式參數**
#@markdown > **設定指揮中心的核心運行參數。**
#@markdown ---
#@markdown **儀表板更新頻率 (秒) (REFRESH_RATE_SECONDS)**
REFRESH_RATE_SECONDS = 1.0 #@param {type:"number"}
#@markdown **時區設定 (TIMEZONE)**
TIMEZONE = "Asia/Taipei" #@param {type:"string"}

# ==============================================================================
# 🚀 核心邏輯
# ==============================================================================

# --- 共享狀態 ---
# 使用 deque 作為日誌緩衝區，自動管理長度
shared_status = {
    "current_task": "初始化中...",
    "logs": deque(maxlen=200), # 增加日誌行數
    "worker_finished": False,
    "worker_error": None,
    "app_process": None,
}
status_lock = threading.Lock()

def update_status(task=None, log=None):
    """安全地更新共享狀態並推送到前端"""
    with status_lock:
        if task is not None:
            shared_status["current_task"] = task
        if log is not None:
            # 為日誌加上時間戳
            timestamp = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')
            shared_status["logs"].append(f"[{timestamp}] {log}")

        # 建立狀態副本以傳遞給 JS
        status_copy = {
            "current_task": shared_status["current_task"],
            "logs": list(shared_status["logs"]),
            "worker_error": shared_status["worker_error"]
        }

    # 使用 JS 更新前端，避免重新渲染整個儲存格
    js_command = f"window.updateFrontend({json.dumps(status_copy)})"
    try:
        colab_output.eval_js(js_command)
    except Exception as e:
        # 在某些情況下 (例如儲存格未完全渲染)，eval_js 可能會失敗
        # print(f"Debug: eval_js failed: {e}")
        pass


def run_command_and_log(command, cwd="."):
    """執行命令並將輸出即時記錄到共享日誌中"""
    update_status(log=f"▶️  執行: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    for line in iter(process.stdout.readline, ''):
        if line:
            update_status(log=f"  > {line.strip()}")

    process.wait()
    if process.returncode != 0:
        error_msg = f"❌ 命令執行失敗，返回碼: {process.returncode}"
        update_status(log=error_msg)
        raise RuntimeError(error_msg)

    update_status(log=f"✅ 命令執行成功。")

def check_and_install_uv():
    """檢查系統中是否存在 uv，如果不存在則自動安裝。"""
    update_status(task="檢查 uv 環境")
    try:
        # 嘗試執行 uv --version，如果成功，則 uv 已安裝
        run_command_and_log(["uv", "--version"])
        update_status(log="✅ uv 已安裝。")
        return
    except (FileNotFoundError, RuntimeError):
        # 如果命令失敗 (通常是 FileNotFoundError)，則表示 uv 未安裝
        update_status(log="⚠️ uv 未安裝，現在開始自動安裝...")
        try:
            # 使用 pip 安裝 uv
            run_command_and_log([sys.executable, "-m", "pip", "install", "-q", "uv"])
            update_status(log="✅ uv 安裝成功！")
        except Exception as e:
            update_status(log=f"❌ uv 安裝失敗: {e}")
            raise

def background_worker():
    """
    在背景執行緒中處理所有耗時任務的簡化版本。
    """
    try:
        # --- 步驟 0: 檢查並安裝 uv ---
        check_and_install_uv()

        # --- 步驟 1: 準備專案環境 ---
        update_status(task="準備專案環境")
        project_path = Path(PROJECT_FOLDER_NAME)

        if FORCE_REPO_REFRESH and project_path.exists():
            update_status(log=f"偵測到強制刷新，正在刪除舊資料夾: {project_path}")
            shutil.rmtree(project_path)
            update_status(log="✅ 舊資料夾已刪除。")

        if not project_path.exists():
            update_status(log=f"正在從 {REPOSITORY_URL} (分支: {TARGET_BRANCH_OR_TAG}) 下載程式碼...")
            run_command_and_log(["git", "clone", "--depth", "1", "--branch", TARGET_BRANCH_OR_TAG, REPOSITORY_URL, str(project_path)])
        else:
            update_status(log="專案資料夾已存在，跳過下載。")

        # --- 步驟 2: 使用 uv 安裝依賴 ---
        update_status(task="安裝專案依賴 (uv)")
        requirements_path = project_path / "requirements.txt"
        if requirements_path.exists():
            # 使用 uv pip install 來高速安裝
            run_command_and_log(["uv", "pip", "install", "-r", str(requirements_path)], cwd=str(project_path))
        else:
            update_status(log=f"⚠️ 找不到 {requirements_path}，跳過依賴安裝。")

        # --- 步驟 3: 執行主應用程式 ---
        update_status(task="啟動主應用程式")
        app_script_path = project_path / "linux_RUN.py"
        if not app_script_path.exists():
            raise FileNotFoundError(f"找不到主應用程式腳本: {app_script_path}")

        update_status(log=f"🚀 正在啟動: {app_script_path}")
        # 使用 Popen 以非阻塞方式執行
        app_process = subprocess.Popen(
            [sys.executable, str(app_script_path)],
            cwd=str(project_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        with status_lock:
            shared_status["app_process"] = app_process

        update_status(task="應用程式運行中", log=f"✅ 主應用程式已在背景啟動 (PID: {app_process.pid})。")

        # 持續讀取應用程式的日誌並推送到前端
        for line in iter(app_process.stdout.readline, ''):
            if line:
                update_status(log=f"  [APP] {line.strip()}")

        app_process.wait()
        update_status(task="應用程式已結束", log=f"返回碼: {app_process.returncode}")

    except Exception as e:
        error_message = f"❌ 背景任務發生致命錯誤: {e}"
        with status_lock:
            shared_status["worker_error"] = str(e)
        update_status(task="背景任務失敗", log=error_message)
    finally:
        with status_lock:
            shared_status["worker_finished"] = True

def render_dashboard_html():
    """生成儀表板的 HTML 和 JS 骨架。"""
    css = """
    <style>
        body { font-family: 'Noto Sans TC', 'Fira Code', monospace; background-color: #1e1e1e; color: #d4d4d4; }
        .container { padding: 1em; }
        .panel { border: 1px solid #444; margin-bottom: 1em; border-radius: 5px; overflow: hidden; }
        .title { font-weight: bold; padding: 0.8em; border-bottom: 1px solid #444; background-color: #2a2a2a;}
        .content { padding: 0.8em; }
        #log-container {
            height: 500px;
            overflow-y: scroll;
            background-color: #1a1a1a;
            padding: 1em;
            border-radius: 4px;
            font-size: 0.9em;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .footer { text-align: center; padding-top: 1em; font-size: 0.8em; color: #888; }
    </style>
    """
    html_body = """
    <div class="container">
        <div class="panel">
            <div class="title">執行狀態</div>
            <div class="content" id="status-content">初始化中...</div>
        </div>
        <div class="panel">
            <div class="title">程序日誌</div>
            <div id="log-container">等待日誌...</div>
        </div>
        <div class="footer" id="footer-status">指揮中心 V25 已啟動</div>
    </div>
    """
    javascript = f"""
    <script type="text/javascript">
        const logContainer = document.getElementById('log-container');
        const statusContent = document.getElementById('status-content');
        const footerStatus = document.getElementById('footer-status');

        window.updateFrontend = function(status) {{
            // 更新狀態
            let statusText = `當前任務: <strong>${{status.current_task || 'N/A'}}</strong>`;
            if (status.worker_error) {{
                statusText += `<br><strong style="color: #f48771;">錯誤: ${{status.worker_error}}</strong>`;
            }}
            statusContent.innerHTML = statusText;

            // 更新日誌
            logContainer.innerHTML = status.logs.join('\\n');
            logContainer.scrollTop = logContainer.scrollHeight; // 自動滾動到底部

            // 更新頁腳
            footerStatus.textContent = `最後更新: ${{new Date().toLocaleTimeString()}}`;
        }};
    </script>
    """
    return f"<head>{css}</head><body>{html_body}{javascript}</body>"

def main():
    """主函數，設定 UI 並啟動背景工作"""
    colab_output.clear_output(wait=True)
    display(HTML(render_dashboard_html()))
    update_status(log="🚀 指揮中心 V25 已啟動。")

    # 啟動背景工作
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()

    try:
        # 主執行緒保持存活，直到背景工作完成或被中斷
        # 背景執行緒會自己更新 UI，所以這裡不需要做太多事
        worker_thread.join()

    except KeyboardInterrupt:
        update_status(task="手動中斷", log="🛑 偵測到使用者手動中斷 (Ctrl+C)。")
        with status_lock:
            app_process = shared_status.get("app_process")

        if app_process and app_process.poll() is None:
            update_status(log="正在嘗試終止背景主應用程式...")
            app_process.terminate()
            try:
                app_process.wait(timeout=5)
                update_status(log="✅ 背景應用程式已關閉。")
            except subprocess.TimeoutExpired:
                update_status(log="⚠️ 關閉超時，強制終止。")
                app_process.kill()
    finally:
        update_status(log="🏁 Colab 指揮中心腳本執行完畢。")

if __name__ == "__main__":
    main()
