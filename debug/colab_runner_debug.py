# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 鳳凰之心 - V44 Colab 指揮中心 (進階除錯與日誌記錄模式)     ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 本腳本為 run/colab_runner.py 的一個修改版，專為深入除錯設計。      ║
# ║ - **核心變更**:                                                      ║
# ║   - 所有操作的詳細輸出 (stdout/stderr) 都會被記錄到一個日誌檔案中。║
# ║   - 這有助於捕捉被 Colab 環境抑制的錯誤訊息。                        ║
# ║   - 日誌檔案位於: debug/colab_runner_debug.log                     ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 💎 鳳凰之心指揮中心 V44 (進階除錯模式) { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 程式碼與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "0.6.2" #@param {type:"string"}
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
# 🚀 核心邏輯 (進階除錯模式)
# ==============================================================================
import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
from datetime import datetime

# 設定日誌檔案路徑
LOG_FILE_PATH = Path(__file__).parent / "colab_runner_debug.log"

def setup_logging():
    """初始化日誌檔案，寫入一個標頭。"""
    header = f"""
# ============================================================================
# 鳳凰之心 - 除錯日誌
# 執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================================================
"""
    with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(header)

def log_message(message, to_console=True):
    """將訊息同時打印到主控台和日誌檔案。"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    if to_console:
        print(log_line, flush=True)
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def run_command(command, **kwargs):
    """
    執行一個子程序指令，並將其 stdout 和 stderr 即時串流至日誌檔案。
    返回一個布林值表示是否成功。
    """
    log_message(f"▶️ 執行指令: {' '.join(command)}")
    log_message(f"▶️ 工作目錄: {kwargs.get('cwd', os.getcwd())}")

    with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
        try:
            process = subprocess.run(
                command,
                stdout=log_file,
                stderr=log_file,
                check=True,
                text=True,
                encoding='utf-8',
                **kwargs
            )
            log_message(f"✅ 指令成功完成: {' '.join(command)}")
            return True
        except FileNotFoundError as e:
            log_message(f"❌ 指令錯誤: 找不到指令 '{command[0]}'")
            log_message(f"--- 錯誤詳情 ---\n{e}\n------------")
            return False
        except subprocess.CalledProcessError as e:
            log_message(f"❌ 指令執行失敗，返回碼: {e.returncode}")
            log_message(f"--- 錯誤詳情記錄在日誌檔案中 ---")
            return False
        except Exception as e:
            log_message(f"❌ 執行指令時發生未預期的錯誤: {e}")
            return False

def setup_environment():
    """
    執行所有耗時的一次性環境準備工作。
    返回準備好的路徑資訊供後續步驟使用。
    """
    log_message("▶️ [階段 1/3] 準備專案環境...")
    base_path = Path(".").resolve()
    project_path = base_path / PROJECT_FOLDER_NAME

    if FORCE_REPO_REFRESH and project_path.exists():
        log_message(f"🗑️ 正在刪除舊資料夾: {project_path}")
        shutil.rmtree(project_path)
        log_message(f"✅ 舊資料夾已刪除。")

    if not project_path.exists():
        log_message(f"⏳ 正在從 Github 下載程式碼至 {project_path}...")
        git_command = ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)]
        if not run_command(git_command):
            return None
        log_message("✅ 程式碼下載成功。")
    else:
        log_message("✅ 專案資料夾已存在，跳過下載。")

    if str(project_path) not in sys.path:
        sys.path.insert(0, str(project_path))

    venv_path = project_path / ".venv"
    if not venv_path.exists():
        log_message(f"⏳ 正在使用 'uv venv' 建立虛擬環境於 {venv_path}...")
        if not run_command(["uv", "venv", str(venv_path)]):
            return None
        log_message("✅ 虛擬環境建立成功。")
    else:
        log_message("✅ 虛擬環境已存在，跳過建立。")

    venv_python = venv_path / "bin" / "python"

    log_message("⏳ 正在使用 uv pip install 安裝所有依賴...")
    core_requirements_path = project_path / "requirements/requirements-core.txt"
    if not core_requirements_path.exists():
        log_message(f"❌ 找不到依賴檔案: {core_requirements_path}")
        return None

    # 使用 'install -r' 而非 'sync'，以確保能正確解析並安裝傳遞依賴項 (transitive dependencies)
    uv_install_command = ["uv", "pip", "install", "--python", str(venv_python), "-r", str(core_requirements_path)]
    if not run_command(uv_install_command, cwd=str(project_path)):
        return None
    log_message("✅ 所有依賴安裝完成。")

    log_message("✅ 環境準備完成。")
    return {"project_path": project_path, "venv_python": venv_python}

def main():
    setup_logging()
    log_message("🚀 指揮中心啟動 (進階除錯模式)...")

    # [第一步] 同步執行環境準備
    env_paths = setup_environment()

    if env_paths:
        log_message("✅ [階段 1/3] 環境準備成功。")

        project_path = env_paths["project_path"]
        venv_python = env_paths["venv_python"]

        # [第二步] 檢查 Uvicorn 是否可以被啟動
        log_message(f"▶️ [階段 2/3] 檢查 Uvicorn 是否能被目標 Python 直譯器找到...")
        check_uvicorn_command = [str(venv_python), "-m", "uvicorn", "--version"]
        if not run_command(check_uvicorn_command, cwd=str(project_path)):
            log_message("❌ Uvicorn 檢查失敗。請檢查日誌檔案以了解詳情。")
            log_message("❌ 啟動流程已中止。")
            return
        log_message("✅ Uvicorn 檢查成功。")

        # [第三步] 直接以阻塞方式啟動後端伺服器
        log_message(f"▶️ [階段 3/3] 嘗試以阻塞模式啟動後端服務...")
        log_message("接下來的輸出將會是 Uvicorn 伺服器的日誌。")
        log_message("如果程式卡住或崩潰，所有輸出都將記錄在日誌檔案中。")

        process_env = os.environ.copy()
        process_env["VIRTUAL_ENV"] = str(venv_python.parent.parent)
        process_env["PATH"] = f"{venv_python.parent}:{process_env.get('PATH', '')}"
        # 確保 Python 輸出是無緩衝的，以便即時寫入日誌
        process_env["PYTHONUNBUFFERED"] = "1"

        uvicorn_command = [
            str(venv_python), "-m", "uvicorn",
            "src.phoenix_core.main:app",
            "--host", "0.0.0.0",
            "--port", str(API_PORT)
        ]

        if not run_command(uvicorn_command, cwd=str(project_path), env=process_env):
             log_message(f"❌ Uvicorn 伺服器執行失敗。請檢查日誌檔案以了解詳情。")
        else:
             log_message("\n✅ 伺服器正常關閉。")

    else:
        log_message("❌ 由於環境準備失敗，啟動流程已中止。")

if __name__ == "__main__":
    main()
