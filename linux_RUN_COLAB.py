# 鳳凰之心 Colab 極簡執行與日誌核心
# 版本: 0.2.0
# 設計目標:
# 1. 絕對簡化：無任何花俏介面，專注於提供純文字日誌。
# 2. 修正匯入錯誤：確保在專案程式碼下載前，不匯入任何專案內部模組。
# 3. 詳細日誌：捕捉並輸出所有命令的詳細過程，便於除錯。
# 4. 穩定性評估：作為一個基礎工具，評估在 Colab 環境下的執行穩定性。
# 5. 完全相容：能在標準 Python 環境中運行，不依賴 Colab 特有功能。

import os
import sys
import subprocess
import time
import logging
import shutil

# --- 全域設定 ---
GIT_REPO_URL = "https://github.com/hsp1234-web/WEB_0802.git"
GIT_BRANCH = "0.1.6"
PROJECT_FOLDER = "WEB_0802"
MONITOR_INTERVAL_SECONDS = 2  # 每 2 秒回報一次狀態

# --- 日誌設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True  # 強制重新設定日誌，避免 Colab 環境中的干擾
)

# --- 核心功能函數 ---

def run_command_with_logging(command, cwd="."):
    """
    執行一個 shell 命令，並將其 stdout 和 stderr 即時串流到日誌中。
    這對於除錯依賴安裝等問題至關重要。
    """
    logging.info(f"▶️  執行命令: {' '.join(command)} (工作目錄: {cwd})")
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 即時讀取並記錄輸出
        for line in iter(process.stdout.readline, ''):
            if line:
                logging.info(f"  > {line.strip()}")

        process.wait()  # 等待命令完全結束
        return_code = process.poll()

        if return_code != 0:
            logging.error(f"❌ 命令執行失敗，返回碼: {return_code}")
            return False

        logging.info(f"✅ 命令執行成功")
        return True

    except FileNotFoundError:
        logging.error(f"❌ 命令未找到: {command[0]}。請確保相關程式已安裝並在系統 PATH 中。")
        return False
    except Exception as e:
        logging.error(f"❌ 執行命令時發生未預期的錯誤: {e}", exc_info=True)
        return False

def setup_environment():
    """
    準備執行環境，包括下載程式碼和安裝依賴。
    """
    logging.info("========================================")
    logging.info("=== 步驟 1: 設定專案環境 ===")
    logging.info("========================================")

    # 步驟 1.1: 下載原始碼
    if os.path.exists(PROJECT_FOLDER):
        logging.info(f"偵測到舊的專案資料夾 '{PROJECT_FOLDER}'，將其刪除以確保全新狀態。")
        try:
            shutil.rmtree(PROJECT_FOLDER)
            logging.info("✅ 舊資料夾已成功刪除。")
        except Exception as e:
            logging.critical(f"❌ 刪除舊資料夾失敗: {e}", exc_info=True)
            return False

    logging.info(f"正在從 {GIT_REPO_URL} (分支: {GIT_BRANCH}) 下載程式碼...")
    git_command = ["git", "clone", "--branch", GIT_BRANCH, GIT_REPO_URL, PROJECT_FOLDER]
    if not run_command_with_logging(git_command):
        logging.critical("❌ Git clone 失敗，腳本無法繼續。")
        return False
    logging.info("✅ 專案原始碼已成功下載。")

    # 步驟 1.2: 安裝依賴
    logging.info("--- 安裝核心依賴 ---")

    # 首先安裝 psutil，供後續監控使用
    pip_psutil_command = [sys.executable, "-m", "pip", "install", "psutil"]
    if not run_command_with_logging(pip_psutil_command):
        logging.critical("❌ 安裝 'psutil' 失敗，無法進行系統監控。")
        return False

    # 接著安裝專案的 requirements.txt
    requirements_path = os.path.join(PROJECT_FOLDER, "requirements.txt")
    if os.path.exists(requirements_path):
        logging.info(f"正在從 {requirements_path} 安裝專案依賴...")
        pip_req_command = [sys.executable, "-m", "pip", "install", "-r", requirements_path]
        if not run_command_with_logging(pip_req_command, cwd=PROJECT_FOLDER):
            logging.critical("❌ 從 requirements.txt 安裝依賴失敗，腳本無法繼續。")
            return False
    else:
        logging.warning(f"⚠️ 找不到 {requirements_path}，跳過專案依賴安裝。")

    logging.info("✅ 所有依賴均已成功安裝。")
    return True

def run_main_application():
    """
    以獨立子程序的方式啟動主應用程式 `linux_RUN.py`。
    """
    logging.info("========================================")
    logging.info("=== 步驟 2: 啟動主應用程式 ===")
    logging.info("========================================")

    app_script_path = os.path.join(PROJECT_FOLDER, "linux_RUN.py")
    if not os.path.exists(app_script_path):
        logging.critical(f"❌ 找不到主應用程式腳本: {app_script_path}，無法啟動。")
        return None

    logging.info("在背景啟動主應用程式...")
    # 將輸出重新導向到檔案，避免與本腳本的日誌混淆
    log_file_path = "application_run.log"
    log_file = open(log_file_path, "w")

    try:
        process = subprocess.Popen(
            [sys.executable, app_script_path],
            cwd=PROJECT_FOLDER,
            stdout=log_file,
            stderr=log_file,
            text=True,
            encoding='utf-8'
        )
        logging.info(f"✅ 主應用程式已在背景啟動 (PID: {process.pid})。")
        logging.info(f"   其日誌將被寫入到 '{log_file_path}' 檔案中。")
        return process
    except Exception as e:
        logging.critical(f"❌ 啟動主應用程式時發生錯誤: {e}", exc_info=True)
        log_file.close()
        return None


def monitor_system(app_process):
    """
    持續監控系統狀態並回報，直到使用者中斷。
    """
    logging.info("========================================")
    logging.info("=== 步驟 3: 進入持續監控模式 ===")
    logging.info("========================================")
    logging.info(f"每 {MONITOR_INTERVAL_SECONDS} 秒回報一次狀態。按 Ctrl+C 來停止腳本與應用程式。")

    try:
        import psutil
    except ImportError:
        logging.error("❌ 監控失敗：無法匯入 'psutil' 模組。")
        return

    try:
        while True:
            # 檢查主應用程式的狀態
            if app_process.poll() is not None:
                logging.warning(f"⚠️ 主應用程式已自行終止，返回碼: {app_process.returncode}。")
                logging.warning("   請檢查 'application_run.log' 檔案以了解詳細原因。")
                break

            # 獲取並記錄系統狀態
            cpu_percent = psutil.cpu_percent(interval=1.0)
            ram_info = psutil.virtual_memory()

            logging.info(
                f"💡 系統狀態 | CPU: {cpu_percent:5.1f}% | "
                f"RAM: {ram_info.percent:5.1f}% ({ram_info.used/1024**2:.0f}MB / {ram_info.total/1024**2:.0f}MB)"
            )

            # 等待下一個間隔
            time.sleep(max(0, MONITOR_INTERVAL_SECONDS - 1.0))

    except KeyboardInterrupt:
        logging.info("\n🛑 偵測到使用者手動中斷 (Ctrl+C)。")
    except Exception as e:
        logging.error(f"❌ 監控迴圈發生未預期的錯誤: {e}", exc_info=True)
    finally:
        logging.info("--- 開始優雅關機 ---")
        if app_process.poll() is None:
            logging.info(f"正在嘗試終止主應用程式 (PID: {app_process.pid})...")
            app_process.terminate()
            try:
                app_process.wait(timeout=5)
                logging.info("✅ 主應用程式已成功關閉。")
            except subprocess.TimeoutExpired:
                logging.warning("⚠️ 關閉超時，將強制終止...")
                app_process.kill()
        else:
            logging.info("主應用程式已經終止，無需操作。")
        logging.info("--- 優雅關機完成 ---")


# --- 主執行流程 ---
def main():
    """腳本的主執行流程"""
    logging.info("🚀 鳳凰之心 Colab 極簡日誌核心已啟動 🚀")

    app_process = None
    try:
        # 步驟 1: 設定環境
        if not setup_environment():
            raise RuntimeError("環境設定失敗，請檢查上述日誌。")

        # 步驟 2: 啟動應用
        app_process = run_main_application()
        if not app_process:
            raise RuntimeError("啟動主應用程式失敗，請檢查上述日誌。")

        # 步驟 3: 監控
        # 給應用程式一點時間啟動
        time.sleep(2)
        monitor_system(app_process)

    except Exception as e:
        logging.critical(f"💥 腳本因無法處理的錯誤而終止: {e}")
    finally:
        logging.info("🏁 腳本執行完畢。")

if __name__ == "__main__":
    main()
