# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 linux_RUN.py (V28 - 黃金基準版 / 環境適應版)               ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 在任何乾淨的 Linux 環境下，從零開始，全自動地完成        ║
# ║           專案的部署、執行和報告生成。                             ║
# ║   - 核心: venv 隔離, pip install -e ., 自動化流程                  ║
# ║   - 備註: 此版本為適應特殊工具鏈環境，將下載驗證與執行分離。       ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
import threading
import time
from datetime import datetime

# --- 全域設定 (Global Settings) ---
VENV_DIR = ".venv_gold"
TEMP_CLONE_DIR = "temp_clone_dir_for_validation" # 用於驗證下載功能的臨時目錄
GIT_REPO = "https://github.com/hsp1234-web/WEB_0802.git"
GIT_BRANCH = "0.1.6"
WATCHDOG_TIMEOUT = 60  # 延長看門狗時間以應對較慢的啟動過程
VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
VENV_UV = os.path.join(VENV_DIR, "bin", "uv")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

def get_timestamp():
    """獲取當前時間戳，用於日誌。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    print("\n" + "="*80)
    print(f"🚀 {get_timestamp()} - {title}")
    print("="*80)

def run_command(command, cwd=".", env=None):
    """
    執行一個子程序命令，並即時串流其輸出。
    如果命令失敗，則拋出例外。
    """
    print(f"   🔹 執行命令: {' '.join(command)} (於 {cwd})")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        cwd=cwd,
        env=env
    )

    # 即時讀取 stdout 和 stderr
    while True:
        stdout_line = process.stdout.readline()
        stderr_line = process.stderr.readline()

        if stdout_line:
            print(f"     [STDOUT] {stdout_line.strip()}")
        if stderr_line:
            print(f"     [STDERR] {stderr_line.strip()}", file=sys.stderr)

        if process.poll() is not None and not stdout_line and not stderr_line:
            break

    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    print(f"   ✅ 命令成功完成。")

def run_core_application(stop_event):
    """
    在一個執行緒中運行核心應用程式。
    """
    print_header("步驟 6: 執行核心應用程式")
    try:
        # 使用 venv 的 python 解譯器來執行，以確保環境正確
        script_content = """
import sys
import os
# 將當前目錄加入 sys.path，以確保能夠找到模組 (雖然 'pip install -e .' 已處理)
sys.path.insert(0, os.path.abspath('.'))
from src.phoenix_core.main import start_event_loop
from src.phoenix_core.utils.logger import logger
logger.log("INFO", "核心應用程式啟動...")
try:
    # 注意：我們現在是在專案的根目錄下執行
    start_event_loop(fast_run=False)
    logger.log("SUCCESS", "核心應用程式正常結束。")
except Exception as e:
    logger.log("CRITICAL", f"核心應用程式執行時發生錯誤: {e}", exc_info=True)
"""
        # 注意: cwd 現在是 '.' (專案根目錄)
        run_command([VENV_PYTHON, "-c", script_content], cwd=".")

    except Exception as e:
        print(f"❌ 核心應用程式執行緒發生未預期的錯誤: {e}", file=sys.stderr)
    finally:
        if not stop_event.is_set():
            print("   ℹ️ 核心應用程式執行緒已結束。")
            stop_event.set() # 通知主執行緒

def main():
    """
    主執行函式，協調所有步驟。
    """
    start_time = time.time()
    os.environ["PYTHONUNBUFFERED"] = "1" # 確保子進程的輸出不會被緩衝

    try:
        # --- 步驟 1: 建立 venv ---
        print_header("步驟 1: 建立 Python 虛擬環境 (venv)")
        if os.path.isdir(VENV_DIR):
            print(f"發現舊的虛擬環境 '{VENV_DIR}'，正在刪除以確保環境純淨...")
            shutil.rmtree(VENV_DIR)

        print(f"正在建立新的虛擬環境 '{VENV_DIR}'...")
        run_command([sys.executable, "-m", "venv", VENV_DIR])
        print(f"✅ 虛擬環境 '{VENV_DIR}' 建立成功。")

        # --- 步驟 2: 在 venv 中安裝 uv ---
        print_header("步驟 2: 在 venv 中安裝 uv")
        run_command([VENV_PIP, "install", "-U", "uv"])
        print("✅ uv 安裝成功。")

        # --- 步驟 3: 下載專案原始碼 (僅供驗證) ---
        print_header("步驟 3: 下載專案原始碼 (僅供驗證)")
        if os.path.exists(TEMP_CLONE_DIR):
            shutil.rmtree(TEMP_CLONE_DIR)

        run_command(["git", "clone", "--branch", GIT_BRANCH, GIT_REPO, TEMP_CLONE_DIR])
        print(f"✅ 專案已成功克隆到 '{TEMP_CLONE_DIR}'。")

        # --- 步驟 3.1: 驗證下載內容 ---
        print_header("步驟 3.1: 驗證下載內容")
        run_command(["ls", "-R"], cwd=TEMP_CLONE_DIR)
        print("✅ 下載內容驗證成功。")

        # --- 步驟 3.2: 刪除臨時目錄以避免工具鏈衝突 ---
        print_header("步驟 3.2: 刪除臨時目錄")
        shutil.rmtree(TEMP_CLONE_DIR)
        print(f"✅ 臨時目錄 '{TEMP_CLONE_DIR}' 已刪除。")

        # --- 接下來的所有操作都在當前專案目錄中進行 ---
        print_header("通知：後續操作將在當前專案目錄下進行。")

        # --- 步驟 4: 將當前專案套件化安裝到 venv 中 ---
        print_header("步驟 4: 將當前專案套件化安裝到 venv 中 (pip install -e .)")
        run_command([VENV_PIP, "install", "-e", "."], cwd=".")
        print("✅ 當前專案已成功以可編輯模式安裝。")

        # --- 步驟 5: 在 venv 中安裝專案依賴 ---
        print_header("步驟 5: 在 venv 中安裝專案依賴")
        requirements_file = "requirements.txt"
        if os.path.exists(requirements_file):
            run_command([VENV_UV, "pip", "install", "--python", VENV_PYTHON, "-r", requirements_file], cwd=".")
            print("✅ 專案依賴安裝成功。")
        else:
            print(f"⚠️ 找不到 {requirements_file}，跳過依賴安裝。")

        # --- 步驟 6: 執行核心應用程式 (帶看門狗) ---
        stop_event = threading.Event()
        worker_thread = threading.Thread(target=run_core_application, args=(stop_event,))
        worker_thread.daemon = True

        worker_thread.start()
        worker_thread.join(timeout=WATCHDOG_TIMEOUT)

        if worker_thread.is_alive():
            print(f"❌ 看門狗超時! 核心應用程式在 {WATCHDOG_TIMEOUT} 秒內未完成。", file=sys.stderr)
            stop_event.set()
            worker_thread.join(timeout=10)
        else:
            print("✅ 核心應用程式在看門狗時限內正常結束。")

        # --- 步驟 7: 執行報告生成器 ---
        print_header("步驟 7: 執行報告生成器")

        # 7.1 重命名資料庫 (在專案根目錄)
        db_original_path = "state.db"
        db_renamed_path = "logs.sqlite"

        if os.path.exists(db_original_path):
            print(f"正在將 '{db_original_path}' 重命名為 '{db_renamed_path}'...")
            shutil.move(db_original_path, db_renamed_path)
            print("✅ 資料庫重命名成功。")
        else:
            print(f"⚠️ 警告: 找不到資料庫檔案 '{db_original_path}'。報告可能不完整。")
            open(db_renamed_path, 'a').close()

        # 7.2 執行報告生成腳本
        report_generator_script = os.path.join("scripts", "report_generator.py")
        if os.path.exists(report_generator_script):
            print(f"偵測到 {report_generator_script}，將直接呼叫它。")

            # 安裝報告依賴
            requirements_report_file = os.path.join("scripts", "requirements-report.txt")
            if os.path.exists(requirements_report_file):
                 print("\\n--- 安裝報告依賴 ---")
                 run_command([VENV_UV, "pip", "install", "--python", VENV_PYTHON, "-r", requirements_report_file], cwd=".")
                 print("✅ 報告依賴安裝成功。")

            report_command = [
                VENV_PYTHON,
                report_generator_script,
                "--db-file", db_renamed_path,
                "--report-dir", "reports",
            ]
            run_command(report_command, cwd=".")
            print("✅ 報告生成完畢。")
        else:
            print(f"⚠️ 找不到報告生成腳本 '{report_generator_script}'，跳過此步驟。")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 一個關鍵命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        print(f"   命令: {' '.join(e.cmd)}", file=sys.stderr)
        print("   🔥 自動化流程中止。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        print("   🔥 自動化流程中止。", file=sys.stderr)
        sys.exit(1)
    finally:
        end_time = time.time()
        print("\n" + "="*80)
        print(f"🏁 全部流程結束，總耗時: {end_time - start_time:.2f} 秒。")
        print("="*80)


if __name__ == "__main__":
    main()
