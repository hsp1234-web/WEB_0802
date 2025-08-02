# 鳳凰之心 Colab 簡易執行與監控腳本
# 版本: 0.1.6
# 設計目標:
# 1. 自動化環境設定 (Git, Python 依賴)。
# 2. 執行核心任務 (測試, 啟動主程式)。
# 3. 提供簡單、線性的日誌輸出，便於在 Colab 中監控。
# 4. 所有訊息使用繁體中文。

import os
import sys
import subprocess
import time
import logging
import shutil

# --- 全域設定 ---
# Git 倉庫資訊
GIT_REPO_URL = "https://github.com/hsp1234-web/WEB_0802.git"
GIT_BRANCH = "0.1.6"
PROJECT_FOLDER = "WEB_0802"

# 監控設定
MONITOR_INTERVAL_SECONDS = 3

# --- 日誌設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)

# --- 核心功能函數 ---

def run_command(command, cwd="."):
    """執行一個 shell 命令並即時串流其輸出"""
    logging.info(f"▶️  執行命令: {' '.join(command)} (於 {cwd})")
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
        # 即時讀取輸出
        for line in iter(process.stdout.readline, ''):
            if line:
                logging.info(f"  > {line.strip()}")

        process.wait() # 等待命令結束
        return_code = process.poll()

        if return_code != 0:
            logging.error(f"❌ 命令執行失敗，返回碼: {return_code}")
            return False
        logging.info(f"✅ 命令執行成功")
        return True
    except FileNotFoundError:
        logging.error(f"❌ 命令未找到: {command[0]}。請確保相關程式已安裝並在 PATH 中。")
        return False
    except Exception as e:
        logging.error(f"❌ 執行命令時發生未預期的錯誤: {e}")
        return False

def setup_project():
    """下載或更新專案程式碼"""
    logging.info("=== 步驟 1: 設定專案原始碼 ===")
    if os.path.exists(PROJECT_FOLDER):
        logging.info(f"資料夾 '{PROJECT_FOLDER}' 已存在，將其刪除以確保全新下載...")
        try:
            shutil.rmtree(PROJECT_FOLDER)
            logging.info(f"✅ 舊資料夾 '{PROJECT_FOLDER}' 已刪除。")
        except Exception as e:
            logging.error(f"❌ 刪除舊資料夾失敗: {e}")
            sys.exit(1)

    logging.info(f"正在從 {GIT_REPO_URL} (分支: {GIT_BRANCH}) 下載程式碼...")
    if not run_command(["git", "clone", "--branch", GIT_BRANCH, GIT_REPO_URL, PROJECT_FOLDER]):
        logging.critical("❌ Git clone 失敗。無法繼續。")
        sys.exit(1)
    logging.info("✅ 專案原始碼設定完成。")
    return True


def install_dependencies():
    """安裝所有必要的 Python 套件"""
    logging.info("=== 步驟 2: 安裝依賴 ===")

    # 首先安裝 psutil，因為監控迴圈需要它
    logging.info("安裝 'psutil' 用於系統監控...")
    if not run_command([sys.executable, "-m", "pip", "install", "psutil"]):
        logging.critical("❌ 安裝 'psutil' 失敗。無法繼續。")
        sys.exit(1)

    # 安裝 requirements.txt 中的依賴
    requirements_path = os.path.join(PROJECT_FOLDER, "requirements.txt")
    if os.path.exists(requirements_path):
        logging.info(f"正在從 {requirements_path} 安裝依賴...")
        if not run_command([sys.executable, "-m", "pip", "install", "-r", requirements_path], cwd=PROJECT_FOLDER):
            logging.critical("❌ 從 requirements.txt 安裝依賴失敗。無法繼續。")
            sys.exit(1)
    else:
        logging.warning(f"⚠️ 找不到 {requirements_path}，跳過依賴安裝。")

    logging.info("✅ 依賴安裝完成。")
    return True

def run_tests():
    """執行 pytest 測試"""
    logging.info("=== 步驟 3: 執行自動化測試 ===")
    if not run_command([sys.executable, "-m", "pytest"], cwd=PROJECT_FOLDER):
        logging.warning("⚠️ 自動化測試失敗或未找到測試。將繼續執行。")
        return False
    logging.info("✅ 自動化測試通過。")
    return True

def start_application():
    """在背景啟動主應用程式"""
    logging.info("=== 步驟 4: 啟動主應用程式 ===")
    app_script_path = os.path.join(PROJECT_FOLDER, "linux_RUN.py")
    if not os.path.exists(app_script_path):
        logging.critical(f"❌ 找不到主應用程式腳本: {app_script_path}。無法啟動。")
        sys.exit(1)

    logging.info("在背景啟動應用程式...")
    # 我們將 stdout 和 stderr 重新導向到檔案，以便之後除錯
    log_file = open("application.log", "w")
    process = subprocess.Popen(
        [sys.executable, app_script_path],
        cwd=PROJECT_FOLDER,
        stdout=log_file,
        stderr=log_file
    )
    logging.info(f"✅ 主應用程式已在背景啟動 (PID: {process.pid})。日誌將被寫入 application.log。")
    return process

def monitor_system(app_process):
    """持續監控系統狀態並回報"""
    logging.info("=== 步驟 5: 進入持續監控模式 ===")
    logging.info(f"每 {MONITOR_INTERVAL_SECONDS} 秒回報一次狀態。按 Ctrl+C 停止。")

    try:
        import psutil
    except ImportError:
        logging.error("❌ 無法匯入 psutil，無法進行監控。")
        return

    try:
        while True:
            # 檢查主應用程式是否還在運行
            if app_process.poll() is not None:
                logging.warning(f"⚠️ 主應用程式似乎已經終止 (返回碼: {app_process.returncode})。請檢查 application.log 以獲得詳細資訊。")
                break

            # 獲取系統狀態
            cpu_percent = psutil.cpu_percent(interval=1)
            ram_info = psutil.virtual_memory()

            logging.info(
                f"💡 系統狀態 - CPU: {cpu_percent:.1f}% | "
                f"RAM: {ram_info.percent:.1f}% ({ram_info.used/1024/1024:.0f}MB / {ram_info.total/1024/1024:.0f}MB)"
            )
            time.sleep(MONITOR_INTERVAL_SECONDS - 1) # 減去 cpu_percent 的 interval

    except KeyboardInterrupt:
        logging.info("\n🛑 偵測到手動中斷 (Ctrl+C)。")
    except Exception as e:
        logging.error(f"❌ 監控迴圈發生錯誤: {e}")
    finally:
        logging.info("正在優雅關閉主應用程式...")
        # 終止子進程
        app_process.terminate()
        try:
            app_process.wait(timeout=5)
            logging.info("✅ 主應用程式已成功關閉。")
        except subprocess.TimeoutExpired:
            logging.warning("關閉超時，強制終止...")
            app_process.kill()
        logging.info("監控結束。")

# --- 主執行流程 ---
def main():
    """主執行函數"""
    try:
        if not setup_project():
            return

        if not install_dependencies():
            return

        run_tests() # 執行測試，但即使失敗也繼續

        app_process = start_application()
        if app_process:
            monitor_system(app_process)

    except Exception as e:
        logging.critical(f"💥 腳本發生無法處理的致命錯誤: {e}")
    finally:
        logging.info("🚀 Colab 執行腳本已結束。")

if __name__ == "__main__":
    main()
