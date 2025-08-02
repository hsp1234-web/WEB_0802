# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║                   📊 離線報告生成器 V28 (穩定後端版)                  ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 說明: 此腳本旨在 Colab 環境中，在 colab_runner.py 執行完畢後   ║
# ║           被單獨執行，以生成最終的任務報告。                         ║
# ║   - 依賴: 它依賴由後端服務產生的資料庫檔案。                       ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import sys
import subprocess
from pathlib import Path
from IPython.display import display, Markdown

#@title 📊 V28 最終任務報告生成器 { vertical-output: true, display-mode: "form" }
#@markdown > **在 `colab_runner` 儲存格執行完畢後，點擊此處以生成報告。**
#@markdown ---
#@markdown ---
#@markdown ### 報告參數
#@markdown > 指定後端服務建立的專案資料夾和資料庫檔案。
#@markdown ---
#@markdown 專案資料夾名稱 (PROJECT_FOLDER_NAME)
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown 資料庫檔案名稱 (DATABASE_FILE)
DATABASE_FILE = "logs.sqlite" #@param {type:"string"}


def find_and_set_project_root():
    """
    在 Colab 環境中，根據 PROJECT_FOLDER_NAME 設定工作目錄。
    如果不在 Colab，則向上搜尋 pyproject.toml。
    """
    # 檢查是否在 Colab 環境
    if 'google.colab' in sys.modules:
        content_root = Path("/content")
        project_path = content_root / PROJECT_FOLDER_NAME
        if project_path.is_dir():
            print(f"✅ 在 Colab 環境中找到專案目錄: {project_path}")
            os.chdir(project_path)
            # 將專案目錄加入到 sys.path 中
            if str(project_path) not in sys.path:
                sys.path.insert(0, str(project_path))
            return project_path
        else:
            raise FileNotFoundError(f"在 /content 中找不到指定的專案資料夾 '{PROJECT_FOLDER_NAME}'。")
    else:
        # 在本地環境，向上搜尋
        current_path = Path.cwd()
        for parent in [current_path] + list(current_path.parents):
            if (parent / "pyproject.toml").exists():
                print(f"✅ 在本地環境中找到專案根目錄: {parent}")
                os.chdir(parent)
                return parent
    raise FileNotFoundError("無法找到專案根目錄。")


def run_report_generator():
    """執行報告生成的主要邏輯。"""
    print("🚀 開始生成報告...")

    try:
        project_root = find_and_set_project_root()
        print(f"当前工作目录: {os.getcwd()}")

        report_script_path = "scripts/generate_report.py"
        db_path = DATABASE_FILE
        report_dir = "reports"
        requirements_path = "requirements/report.txt"
        venv_python = ".venv_colab_backend/bin/python"

        # 1. 檢查必要的檔案是否存在
        if not Path(report_script_path).exists():
            raise FileNotFoundError(f"找不到報告生成腳本: {report_script_path}")
        if not Path(db_path).exists():
            raise FileNotFoundError(f"找不到資料庫檔案: {db_path}。請確認後端服務已成功執行並產生資料庫。")
        if not Path(venv_python).exists():
             raise FileNotFoundError(f"找不到後端虛擬環境: {venv_python}。請確認 colab_runner 已成功執行。")

        print("✅ 必要檔案均已找到。")

        # 2. 安裝報告所需的依賴到後端的 venv 中
        print("\n--- 正在安裝報告依賴 (如果需要)... ---")
        subprocess.run(
            [venv_python, "-m", "pip", "install", "-q", "-r", requirements_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ 報告依賴已就緒。")

        # 3. 執行報告生成腳本
        print("\n--- 正在執行報告生成腳本... ---")
        report_process = subprocess.run(
            [
                venv_python,
                report_script_path,
                "--db-file", db_path,
                "--report-dir", report_dir,
            ],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ 報告生成腳本執行成功。")
        print("\n--- 腳本輸出 ---")
        print(report_process.stdout)

        # 4. 顯示報告
        print("\n--- 顯示報告 ---")
        summary_report_path = Path(report_dir) / "summary_report.md"
        if summary_report_path.exists():
            display(Markdown(f"## 📊 綜合戰情簡報"))
            with open(summary_report_path, 'r', encoding='utf-8') as f:
                display(Markdown(f.read()))
        else:
            print(f"⚠️ 找不到總結報告檔案: {summary_report_path}")

    except FileNotFoundError as e:
        print(f"\n❌ 錯誤: {e}")
    except subprocess.CalledProcessError as e:
        print("\n❌ 報告生成過程中發生錯誤。")
        print(f"返回碼: {e.returncode}")
        print("--- STDOUT ---")
        print(e.stdout)
        print("--- STDERR ---")
        print(e.stderr)
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}")

    print("\n🏁 報告生成結束。")

# --- 主執行區 ---
if __name__ == "__main__":
    run_report_generator()
