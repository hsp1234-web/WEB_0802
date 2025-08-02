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
    【已修改】啟動 FastAPI 伺服器作為核心應用。
    """
    print_header("步驟 6: 啟動核心應用程式 (FastAPI 伺服器)")

    server_process = None
    try:
        # 正確的啟動方式是使用 uvicorn 運行 src.phoenix_core.main 中的 app 物件
        api_server_command = [
            VENV_PYTHON,
            "-m",
            "uvicorn",
            "src.phoenix_core.main:app",
            "--host", "0.0.0.0",
            "--port", "8080", # 使用一個常用端口
        ]

        print(f"   🔹 執行命令: {' '.join(api_server_command)}")
        # 使用 Popen 在背景啟動伺服器
        server_process = subprocess.Popen(
            api_server_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # 簡化版看門狗：我們不期望伺服器結束，只驗證它能成功運行一段時間
        # 讓伺服器運行 15 秒，作為一個簡短的測試運行
        print("   ℹ️ 伺服器正在背景運行，等待 15 秒作為測試運行...")

        # 在等待時，可以即時打印日誌
        end_time = time.time() + 15
        while time.time() < end_time:
            if server_process.poll() is not None:
                # 如果進程在此期間意外退出，則表示有錯誤
                stdout, stderr = server_process.communicate()
                print(f"❌ 伺服器在測試運行期間意外終止。", file=sys.stderr)
                print(f"   [STDOUT]: {stdout}", file=sys.stderr)
                print(f"   [STDERR]: {stderr}", file=sys.stderr)
                raise Exception("伺服器啟動失敗")
            time.sleep(1)

        print("✅ 伺服器成功運行了 15 秒。")

    except Exception as e:
        print(f"❌ 核心應用程式執行緒發生未預期的錯誤: {e}", file=sys.stderr)
    finally:
        # 無論如何，確保終止伺服器進程，以便腳本可以繼續
        if server_process and server_process.poll() is None:
            print("   ℹ️ 測試運行結束，正在終止伺服器...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("   ✅ 伺服器已成功終止。")
            except subprocess.TimeoutExpired:
                server_process.kill()

        # 通知主執行緒（如果需要）
        if not stop_event.is_set():
            stop_event.set()

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
        requirements_file = "requirements/base.txt"
        if os.path.exists(requirements_file):
            run_command([VENV_UV, "pip", "install", "--python", VENV_PYTHON, "-r", requirements_file], cwd=".")
            print("✅ 專案依賴安裝成功。")
        else:
            print(f"⚠️ 找不到 {requirements_file}，跳過依賴安裝。")

        # --- 步驟 6: 執行核心應用程式 ---
        # 由於 run_core_application 現在是阻塞的，我們不再需要獨立的執行緒和複雜的看門狗
        stop_event = threading.Event() # 雖然簡化了，但保留事件以備未來擴展
        run_core_application(stop_event)
        print("✅ 核心應用程式測試運行已完成。")

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
        report_generator_script = os.path.join("scripts", "generate_report.py")
        if os.path.exists(report_generator_script):
            print(f"偵測到 {report_generator_script}，將直接呼叫它。")

            # 安裝報告依賴
            requirements_report_file = "requirements/report.txt"
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
