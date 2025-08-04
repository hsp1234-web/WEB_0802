# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║    🚀 鳳凰之心 - V47 Colab 互動式啟動器 (代理模式)                 ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - V47 更新日誌:                                                      ║
# ║   - **架構重構**: 引入背景執行緒、HTML輸出與 Colab 代理連結。      ║
# ║   - **交互優化**: 提供清晰的狀態面板與可點擊的公開網址。           ║
# ║   - V46: 改用 pip install 解決依賴問題，更新分支至 0.6.5。         ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 💎 鳳凰之心指揮中心 V47 (代理連結模式) { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 程式碼與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "0.6.5" #@param {type:"string"}
#@markdown **專案資料夾名稱 (PROJECT_FOLDER_NAME)**
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown **強制刷新後端程式碼 (FORCE_REPO_REFRESH)**
FORCE_REPO_REFRESH = True #@param {type:"boolean"}

#@markdown ---
#@markdown ### Part 2: 應用程式參數
#@markdown > **設定指揮中心的核心運行參數。**
#@markdown ---
#@markdown **後端 API 服務埠號 (API_PORT)**
API_PORT = 8088 #@param {type:"integer"}

# ==============================================================================
# 🚀 核心邏輯 (互動模式)
# ==============================================================================
import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import json
from datetime import datetime
import threading
from IPython.display import display, HTML, clear_output
from google.colab import output as colab_output

# --- 全域變數 ---
SERVER_PROCESS_GLOBAL = None

# --- 伺服器控制函式 ---
def stop_server():
    """停止 Uvicorn 伺服器進程。"""
    global SERVER_PROCESS_GLOBAL
    if SERVER_PROCESS_GLOBAL and SERVER_PROCESS_GLOBAL.poll() is None:
        display(HTML("<p>⏳ 正在嘗試終止舊的伺服器進程...</p>"))
        try:
            # 使用 os.killpg 發送 SIGTERM 到整個進程組，更可靠
            os.killpg(os.getpgid(SERVER_PROCESS_GLOBAL.pid), subprocess.signal.SIGTERM)
            SERVER_PROCESS_GLOBAL.wait(timeout=10)
            display(HTML("<p>✅ 舊伺服器已溫和終止。</p>"))
        except (subprocess.TimeoutExpired, ProcessLookupError):
            display(HTML("<p>⚠️ 溫和終止超時，嘗試強制停止...</p>"))
            try:
                os.killpg(os.getpgid(SERVER_PROCESS_GLOBAL.pid), subprocess.signal.SIGKILL)
                SERVER_PROCESS_GLOBAL.wait(timeout=5)
                display(HTML("<p>✅ 舊伺服器已被強制停止。</p>"))
            except Exception as e_kill:
                display(HTML(f"<p>❌ 強制停止失敗: {e_kill}</p>"))
        finally:
            SERVER_PROCESS_GLOBAL = None
    else:
        display(HTML("<p>ⓘ 沒有正在執行的舊伺服器。</p>"))


def display_status(message, msg_type="info"):
    """使用 HTML 顯示格式化的狀態訊息。"""
    colors = {
        "info": "#89b4f8",
        "success": "#81c995",
        "error": "#f28b82",
        "warn": "#fdd663"
    }
    color = colors.get(msg_type, "#e8eaed")
    display(HTML(f"<p style='color: {color}; margin: 2px 0;'>{message}</p>"))

def setup_environment():
    """
    執行所有耗時的一次性環境準備工作。
    此函式會同步執行，直到所有步驟完成或發生錯誤。
    返回準備好的路徑資訊供後續步驟使用。
    """
    try:
        display_status("▶️ [階段 1/3] 準備專案環境...")
        base_path = Path(".").resolve()
        project_path = base_path / PROJECT_FOLDER_NAME

        if FORCE_REPO_REFRESH and project_path.exists():
            shutil.rmtree(project_path)
            display_status("🗑️ 舊資料夾已刪除。")

        if not project_path.exists():
            display_status(f"⏳ 正在從 Github 下載程式碼 (分支: {TARGET_BRANCH_OR_TAG})...")
            git_command = ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)]
            result = subprocess.run(git_command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                display_status(f"❌ Git clone 失敗。返回碼: {result.returncode}", "error")
                display(HTML(f"<pre style='color:#f28b82;'>{result.stderr}</pre>"))
                return None
            display_status("✅ 程式碼下載成功。")
        else:
            display_status("✅ 專案資料夾已存在，跳過下載。")

        if str(project_path) not in sys.path:
            sys.path.insert(0, str(project_path))

        venv_path = project_path / ".venv"
        if not venv_path.exists():
            display_status(f"⏳ 正在使用 'uv venv' 建立虛擬環境...")
            result = subprocess.run(["uv", "venv", str(venv_path)], check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                display_status(f"❌ 建立虛擬環境失敗。", "error")
                display(HTML(f"<pre style='color:#f28b82;'>{result.stderr}</pre>"))
                return None
            display_status("✅ 虛擬環境建立成功。")
        else:
            display_status("✅ 虛擬環境已存在。")

        venv_python = (venv_path / "bin" / "python").resolve()

        display_status("⏳ 正在使用 'pip' 安裝核心依賴...")
        core_requirements_path = project_path / "requirements/requirements-core.txt"
        if not core_requirements_path.exists():
            display_status(f"❌ 找不到依賴檔案: {core_requirements_path}", "error")
            return None

        pip_install_command = [str(venv_python), "-m", "pip", "install", "-r", str(core_requirements_path)]
        result = subprocess.run(pip_install_command, check=False, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            display_status(f"❌ 使用 pip 安裝依賴失敗。", "error")
            display(HTML(f"<pre style='color:#f28b82;'>{result.stderr}</pre>"))
            return None
        display_status("✅ 核心依賴安裝完成。", "success")
        return {"project_path": project_path, "venv_python": venv_python}

    except Exception as e:
        display_status(f"❌ 在環境準備階段發生致命錯誤: {e}", "error")
        return None

def main():
    """主執行函式，負責啟動和管理伺服器。"""
    clear_output(wait=True)
    display(HTML("<h2 style='color: #89b4f8;'>🚀 鳳凰之心 V47 互動式啟動器</h2>"))

    try:
        # 確保任何先前的實例都被關閉
        stop_server()
        time.sleep(1)

        env_paths = setup_environment()

        if env_paths:
            display_status("✅ [階段 2/3] 環境準備成功。", "success")
            display_status("⏳ [階段 3/3] 正在啟動後端服務...")

            project_path = env_paths["project_path"]
            venv_python = env_paths["venv_python"]

            process_env = os.environ.copy()
            process_env["VIRTUAL_ENV"] = str(venv_python.parent.parent)
            process_env["PATH"] = f"{venv_python.parent}:{process_env.get('PATH', '')}"
            process_env["PYTHONUNBUFFERED"] = "1"

            uvicorn_command = [
                str(venv_python), "-m", "uvicorn",
                "src.phoenix_core.main:app",
                "--host", "0.0.0.0",
                "--port", str(API_PORT),
                "--workers", "1" # 在 Colab 環境中，單一 worker 通常更穩定
            ]

            global SERVER_PROCESS_GLOBAL
            SERVER_PROCESS_GLOBAL = subprocess.Popen(
                uvicorn_command,
                cwd=str(project_path),
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                preexec_fn=os.setsid
            )

            display_status(f"✅ [階段 3/3] 伺服器已在背景啟動 (PID: {SERVER_PROCESS_GLOBAL.pid})。", "success")
            time.sleep(5) # 等待伺服器初始化

            # 產生代理連結
            colab_output.serve_kernel_port_as_window(
                API_PORT,
                path='/',
                anchor_text=f'🚀 點此開啟鳳凰之心應用程式 (連接埠 {API_PORT})'
            )

            display(HTML("<hr style='border-color: #5f6368; margin-top: 15px;'>"))
            display(HTML("<p style='color: #e8eaed;'>伺服器正在運行中... 您可以點擊上方連結訪問應用程式。</p>"))
            display(HTML("<p style='color: #fdd663;'><b>⚠️ 若要停止伺服器，請點擊此儲存格執行按鈕左側的「中斷執行」方塊。</b></p>"))

            # 保持主執行緒存活，直到使用者手動中斷
            while SERVER_PROCESS_GLOBAL.poll() is None:
                time.sleep(1)

            # 如果迴圈結束，表示進程已終止
            display_status("伺服器進程已終止。", "warn")

        else:
            display_status("❌ 由於環境準備失敗，啟動流程已中止。", "error")

    except KeyboardInterrupt:
        display_status("🛑 偵測到使用者手動中斷...", "warn")
    except Exception as e:
        display_status(f"❌ 發生未預期的致命錯誤: {e}", "error")
    finally:
        display_status("ℹ️ 正在執行清理程序...", "info")
        stop_server()
        display(HTML("<hr><p>所有任務已結束。</p>"))

if __name__ == "__main__":
    main()
