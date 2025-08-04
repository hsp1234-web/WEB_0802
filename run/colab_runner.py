# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║        🚀 鳳凰之心 - V45 Colab 指揮中心 (純文字除錯模式)           ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - V45 更新日誌:                                                      ║
# ║   - **分支更新**: 將預設分支從 0.6.2 更新至 0.6.4。                ║
# ║   - **依賴安裝修正**: 改善 `uv pip sync` 的執行方式，提高相容性。  ║
# ║   - V44: 移除UI，改為同步阻塞，專注於除錯。                      ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 💎 鳳凰之心指揮中心 V45 (純文字除錯模式) { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 程式碼與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "0.6.4" #@param {type:"string"}
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
# 🚀 核心邏輯 (除錯模式)
# ==============================================================================
import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import json
from datetime import datetime

def log_message(message, level="INFO"):
    """一個簡單的日誌函式，直接打印到標準輸出。"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}", flush=True)

def setup_environment():
    """
    執行所有耗時的一次性環境準備工作。
    此函式會同步執行，直到所有步驟完成或發生錯誤。
    返回準備好的路徑資訊供後續步驟使用。
    """
    try:
        log_message("▶️ [階段 1/2] 準備專案環境...")
        base_path = Path(".").resolve()
        project_path = base_path / PROJECT_FOLDER_NAME

        if FORCE_REPO_REFRESH and project_path.exists():
            shutil.rmtree(project_path)
            log_message(f"🗑️ 舊資料夾已刪除: {project_path}")

        if not project_path.exists():
            log_message(f"⏳ 正在從 Github 下載程式碼 (分支: {TARGET_BRANCH_OR_TAG})...")
            git_command = ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)]
            result = subprocess.run(git_command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                log_message(f"❌ Git clone 失敗。返回碼: {result.returncode}", level="ERROR")
                log_message(f"--- STDERR ---\n{result.stderr}\n------------", level="ERROR")
                return None
            log_message("✅ 程式碼下載成功。")
        else:
            log_message("✅ 專案資料夾已存在，跳過下載。")

        if str(project_path) not in sys.path:
            sys.path.insert(0, str(project_path))

        venv_path = project_path / ".venv"
        if not venv_path.exists():
            log_message(f"⏳ 正在使用 'uv venv' 建立虛擬環境於 {venv_path}...")
            result = subprocess.run(["uv", "venv", str(venv_path)], check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                log_message(f"❌ 建立虛擬環境失敗。返回碼: {result.returncode}", level="ERROR")
                log_message(f"--- STDERR ---\n{result.stderr}\n------------", level="ERROR")
                return None
            log_message("✅ 虛擬環境建立成功。")
        else:
            log_message("✅ 虛擬環境已存在，跳過建立。")

        venv_python = (venv_path / "bin" / "python").resolve()

        log_message("⏳ 正在使用 uv 安裝/同步核心依賴...")
        core_requirements_path = project_path / "requirements/requirements-core.txt"
        if not core_requirements_path.exists():
            log_message(f"❌ 找不到依賴檔案: {core_requirements_path}", level="ERROR")
            return None

        install_env = os.environ.copy()
        install_env["VIRTUAL_ENV"] = str(venv_path)
        install_env["PATH"] = f"{venv_path / 'bin'}:{install_env.get('PATH', '')}"

        uv_install_command = ["uv", "pip", "sync", str(core_requirements_path)]

        result = subprocess.run(
            uv_install_command,
            check=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=install_env
        )
        if result.returncode != 0:
            log_message(f"❌ 安裝依賴失敗。返回碼: {result.returncode}", level="ERROR")
            log_message(f"--- STDERR ---\n{result.stderr}\n------------", level="ERROR")
            return None
        log_message("✅ 核心依賴安裝完成。")

        log_message("✅ 環境準備完成。")
        return {"project_path": project_path, "venv_python": venv_python}

    except Exception as e:
        log_message(f"❌ 在環境準備階段發生致命錯誤: {e}", level="ERROR")
        return None

def main():
    log_message("🚀 指揮中心啟動 (純文字除錯模式)...")

    env_paths = setup_environment()

    if env_paths:
        log_message("✅ [階段 1/2] 環境準備成功。")

        project_path = env_paths["project_path"]
        venv_python = env_paths["venv_python"]

        log_message(f"▶️ [階段 2/2] 嘗試以阻塞模式啟動後端服務...")
        log_message("您應該會在這裡看到 Uvicorn 伺服器的日誌。")
        log_message("如果程式卡在這裡且沒有任何輸出，代表伺服器啟動時可能發生了問題。")

        process_env = os.environ.copy()
        process_env["VIRTUAL_ENV"] = str(venv_python.parent.parent)
        process_env["PATH"] = f"{venv_python.parent}:{process_env.get('PATH', '')}"
        process_env["PYTHONUNBUFFERED"] = "1"

        try:
            uvicorn_command = [
                str(venv_python), "-m", "uvicorn",
                "src.phoenix_core.main:app",
                "--host", "0.0.0.0",
                "--port", str(API_PORT)
            ]

            subprocess.run(
                uvicorn_command,
                cwd=str(project_path),
                env=process_env,
                check=True
            )
        except subprocess.CalledProcessError as e:
            log_message(f"❌ Uvicorn 伺服器執行失敗，返回碼: {e.returncode}", level="ERROR")
        except KeyboardInterrupt:
            log_message("\n✅ 手動中斷，程式結束。")
        except Exception as e:
            log_message(f"❌ 啟動伺服器時發生未預期的錯誤: {e}", level="ERROR")

    else:
        log_message("❌ 由於環境準備失敗，啟動流程已中止。")

if __name__ == "__main__":
    main()
