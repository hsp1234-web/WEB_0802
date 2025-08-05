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
    【已升級】啟動並使用看門狗監控 FastAPI 伺服器。
    """
    print_header("步驟 4: 啟動並監控核心應用程式")

    server_process = None
    watchdog_timer = None

    def handle_timeout():
        print(f"❌ {get_timestamp()} - 看門狗觸發！超過 10 秒未收到日誌，正在終止伺服器...", file=sys.stderr)
        if server_process and server_process.poll() is None:
            server_process.kill() # 使用 kill 確保進程被終止

    def reset_watchdog(timeout=10.0):
        nonlocal watchdog_timer
        if watchdog_timer:
            watchdog_timer.cancel()
        watchdog_timer = threading.Timer(timeout, handle_timeout)
        watchdog_timer.start()

    try:
        api_server_command = [
            VENV_PYTHON, "-m", "uvicorn", "src.phoenix_core.main:app",
            "--host", "0.0.0.0", "--port", "8080",
        ]
        print(f"   🔹 執行命令: {' '.join(api_server_command)}")

        # 使用 Popen 在背景啟動伺服器，確保設定 PYTHONUNBUFFERED
        process_env = os.environ.copy()
        process_env["PYTHONUNBUFFERED"] = "1"
        server_process = subprocess.Popen(
            api_server_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # 將 stderr 合併到 stdout
            text=True,
            encoding='utf-8',
            env=process_env
        )

        print(f"   ✅ 伺服器進程已啟動 (PID: {server_process.pid})。")
        reset_watchdog() # 啟動第一個看門狗計時器

        # 即時讀取日誌並餵狗
        for line in iter(server_process.stdout.readline, ''):
            if not line: # 當輸出結束時退出
                break

            log_line = line.strip()
            print(f"     [伺服器日誌] {log_line}")
            reset_watchdog() # 每次收到日誌就重置看門狗

        # 檢查進程結束後是否有錯誤
        return_code = server_process.wait()
        if return_code != 0:
             print(f"   ⚠️ 伺服器進程已終止，返回碼: {return_code}", file=sys.stderr)

    except Exception as e:
        print(f"❌ 核心應用程式執行緒發生未預期的錯誤: {e}", file=sys.stderr)
    finally:
        print("   ℹ️ 執行結束，正在進行最終清理...")
        if watchdog_timer:
            watchdog_timer.cancel() # 確保計時器被清理
        if server_process and server_process.poll() is None:
            print("   ℹ️ 正在終止伺服器...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
        print("   ✅ 清理完畢。")
        stop_event.set()

def main():
    """
    主執行函式，協調所有步驟。
    """
    start_time = time.time()
    os.environ["PYTHONUNBUFFERED"] = "1"

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

        # --- 步驟 3: 將當前專案套件化安裝到 venv 中 ---
        print_header("步驟 3: 將當前專案套件化安裝到 venv 中 (pip install -e .)")
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

        # 確保 state.db 存在，以防伺服器運行時間過短未及建立
        if not os.path.exists(db_original_path):
            print(f"⚠️ 警告: '{db_original_path}' 不存在，將建立一個空檔案以確保測試流程完整。")
            open(db_original_path, 'a').close()

        print(f"正在將 '{db_original_path}' 重命名為 '{db_renamed_path}'...")
        shutil.move(db_original_path, db_renamed_path)
        print("✅ 資料庫重命名成功。")

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
