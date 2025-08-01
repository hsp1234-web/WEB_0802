# 檔案: tests/e2e/test_full_lifecycle.py
# 說明: 模擬從啟動到報告的完整使用者流程，以進行端對端驗證。 (修正版 3)
# 作者: Jules

import subprocess
import sys
import os
import time
import signal
import shutil
from pathlib import Path

# --- 顏色和日誌 ---
class Color:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'

def log_info(message):
    print(f"{Color.GREEN}[INFO] {message}{Color.ENDC}")

def log_warn(message):
    print(f"{Color.YELLOW}[WARN] {message}{Color.ENDC}")

def log_error(message):
    print(f"{Color.RED}[ERROR] {message}{Color.ENDC}")

# --- 測試設定 ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_CONTENT_DIR = PROJECT_ROOT / "tmp_e2e_test"
PROJECT_FOLDER_NAME = "WEB1_E2E_TEST"
PROJECT_PATH = TMP_CONTENT_DIR / PROJECT_FOLDER_NAME
RUN_TIME_SECONDS = 15
VENV_PYTHON_PATH = PROJECT_ROOT / ".venv" / "bin" / "python"

# --- 主測試函式 ---
def main():
    """執行完整的端對端測試流程。"""

    process = None # 確保 process 在 try 區塊外被定義
    try:
        # --- 1. 環境準備 ---
        log_info("--- 步驟 1: 環境準備 ---")
        if TMP_CONTENT_DIR.exists():
            shutil.rmtree(TMP_CONTENT_DIR)
        TMP_CONTENT_DIR.mkdir()

        # 複製整個專案到一個模擬的 git clone 目錄
        shutil.copytree(PROJECT_ROOT, PROJECT_PATH, ignore=shutil.ignore_patterns('.venv', 'tmp_e2e_test', '.git', '__pycache__'))
        os.chdir(PROJECT_PATH) # 進入模擬的專案目錄
        log_info(f"臨時 Colab 環境已建立於: {PROJECT_PATH}")

        # --- 2. 模擬 colab_runner.py ---
        log_info(f"--- 步驟 2: 模擬執行 run/colab_runner.py (將運行 {RUN_TIME_SECONDS} 秒) ---")
        colab_runner_path = PROJECT_PATH / "run" / "colab_runner.py"

        # 我們需要修改 colab_runner.py 來禁用 git clone 和設定正確的 project folder
        with open(colab_runner_path, "r", encoding="utf-8") as f:
            runner_content = f.read()

        runner_content = runner_content.replace(
            'PROJECT_FOLDER_NAME = "WEB1"',
            f'PROJECT_FOLDER_NAME = "{PROJECT_FOLDER_NAME}"'
        ).replace(
            'base_path = Path("/content")',
            f'base_path = Path("{TMP_CONTENT_DIR}")'
        ).replace(
            'if FORCE_REPO_REFRESH and project_path.exists():',
            'if False: # E2E Test'
        ).replace(
            'if not project_path.exists():',
            'if False: # E2E Test'
        )
        with open(colab_runner_path, "w", encoding="utf-8") as f:
            f.write(runner_content)

        command = [str(VENV_PYTHON_PATH), str(colab_runner_path)]
        log_info(f"執行指令: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            stdout=sys.stdout, # 直接輸出到主控台方便即時觀察
            stderr=sys.stderr,
            text=True,
            encoding='utf-8'
        )

        # --- 3. 模擬使用者中斷 ---
        log_info(f"--- 步驟 3: 等待 {RUN_TIME_SECONDS} 秒後，模擬使用者中斷 (Ctrl+C) ---")
        time.sleep(RUN_TIME_SECONDS)

        log_info(f"發送 SIGINT 信號至進程 (PID: {process.pid})")
        process.send_signal(signal.SIGINT)

        log_info("等待進程結束...")
        process.wait(timeout=20)
        log_info("進程已結束。")

        # --- 4. 驗證 state.db ---
        log_info("--- 步驟 4: 驗證 state.db 是否生成 ---")
        db_path = PROJECT_PATH / "state.db"
        if not db_path.exists():
            log_error(f"測試失敗: state.db 未在 {db_path} 中生成。")
            sys.exit(1)
        log_info(f"✅ 成功找到 state.db 於: {db_path}")

        # --- 5. 模擬 report.py ---
        log_info("--- 步驟 5: 模擬執行 run/report.py ---")
        report_script_path = PROJECT_PATH / "run" / "report.py"

        with open(report_script_path, "r", encoding="utf-8") as f:
            report_content = f.read()
        report_content = report_content.replace(
            'PROJECT_FOLDER_NAME = "WEB1"',
            f'PROJECT_FOLDER_NAME = "{PROJECT_FOLDER_NAME}"'
        ).replace(
            'content_root = Path("/content")',
            f'content_root = Path("{TMP_CONTENT_DIR}")'
        )
        with open(report_script_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        report_command = [str(VENV_PYTHON_PATH), str(report_script_path)]
        log_info(f"執行指令: {' '.join(report_command)}")

        report_result = subprocess.run(
            report_command,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        print("\n--- report.py STDOUT ---")
        print(report_result.stdout)
        if report_result.stderr:
            print("\n--- report.py STDERR ---")
            print(report_result.stderr)

        if report_result.returncode != 0:
            log_error("測試失敗: run/report.py 執行時返回非零代碼。")
            sys.exit(1)

        # --- 6. 最終驗證 ---
        log_info("--- 步驟 6: 最終驗證報告檔案是否生成 ---")
        reports_dir = PROJECT_PATH / "reports"
        expected_reports = ["summary_report.md", "performance_report.md", "detailed_log_report.md"]

        all_reports_found = True
        for report_name in expected_reports:
            report_path = reports_dir / report_name
            if report_path.exists():
                log_info(f"✅ 成功找到報告: {report_name}")
            else:
                log_error(f"❌ 找不到報告: {report_name}")
                all_reports_found = False

        if all_reports_found:
            log_info("🎉 端對端生命週期測試成功！")
            sys.exit(0)
        else:
            log_error("💥 端對端生命週期測試失敗。")
            sys.exit(1)

    finally:
        # --- 清理 ---
        if process and process.poll() is None:
            log_warn("測試結束時，子進程仍在運行。強制終止。")
            process.kill()

        os.chdir(PROJECT_ROOT) # 切換回原始目錄
        if TMP_CONTENT_DIR.exists():
            shutil.rmtree(TMP_CONTENT_DIR)
            log_info("臨時目錄已刪除。")

if __name__ == "__main__":
    main()
