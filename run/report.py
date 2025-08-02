# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║                   📊 離線報告生成器 V29 (測試強化版)                  ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 說明: 此腳本旨在 Colab 環境中，在 colab_runner.py 執行完畢後   ║
# ║           被單獨執行，以生成最終的任務報告。                         ║
# ║   - 依賴: 它依賴由後端服務產生的 `state.db` (或 `logs.sqlite`)。   ║
# ║   - 更新: 已整合至 E2E 測試流程中。                                ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import sys
import subprocess
from IPython.display import display, Markdown

#@title 📊 V29 最終任務報告生成器 { vertical-output: true, display-mode: "form" }
#@markdown > **在 `colab_runner` 儲存格執行完畢後，點擊此處以生成報告。**
#@markdown ---

print("🚀 開始生成報告...")

# 在新的架構中，實際的報告生成邏輯由 `scripts/generate_report.py` 處理。
# 這個 Colab 腳本只是一個簡單的觸發器。

report_script_path = "scripts/generate_report.py"
db_path = "logs.sqlite" # 假設後端服務已將 state.db 重命名
report_dir = "reports"
requirements_path = "requirements/report.txt"
venv_python = ".venv_colab_backend/bin/python" # 使用後端建立的 venv

# 1. 檢查必要的檔案是否存在
if not os.path.exists(report_script_path):
    print(f"❌ 錯誤: 找不到報告生成腳本: {report_script_path}")
elif not os.path.exists(db_path):
    print(f"❌ 錯誤: 找不到資料庫檔案: {db_path}。請確認後端服務已成功執行。")
else:
    try:
        print("✅ 必要檔案均已找到。")

        # 2. 安裝報告所需的依賴到後端的 venv 中
        print("\n--- 正在安裝報告依賴 (如果需要)... ---")
        subprocess.run(
            [venv_python, "-m", "pip", "install", "-r", requirements_path],
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
        summary_report_path = os.path.join(report_dir, "summary_report.md")
        if os.path.exists(summary_report_path):
            display(Markdown(f"## 📊 綜合戰情簡報"))
            display(Markdown(summary_report_path.read_text(encoding='utf-8')))
        else:
            print(f"⚠️ 找不到總結報告檔案: {summary_report_path}")

    except subprocess.CalledProcessError as e:
        print("\n❌ 報告生成過程中發生錯誤。")
        print(f"返回碼: {e.returncode}")
        print("--- STDOUT ---")
        print(e.stdout)
        print("--- STDERR ---")
        print(e.stderr)
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")

print("\n🏁 報告生成結束。")
