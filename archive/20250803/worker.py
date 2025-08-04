# -*- coding: utf-8 -*-
"""
鳳凰之心核心工作執行緒 (Phoenix Heart Core Worker Thread)

這個模組包含在背景執行緒中運行的主要業務邏輯，
包括安裝依賴、執行測試和模擬核心應用程式任務。
"""
import subprocess
import sys
import time
from datetime import datetime
import threading
import pytz
from pathlib import Path

from src.phoenix_core.utils.logger import logger

# --- 常數定義 ---
PIP_INSTALL_TIMEOUT_PER_PACKAGE = 45  # 每個套件的安裝超時時間(秒)
PYTEST_EXECUTION_TIMEOUT = 180        # 整體測試執行的超時時間(秒)
LOG_ARCHIVE_DIR = Path("paper")       # 日誌歸檔目錄

def _archive_log():
    """
    將當前執行的日誌歸檔到指定的資料夾。
    """
    try:
        logger.log("INFO", f"正在將日誌歸檔到 '{LOG_ARCHIVE_DIR}' 資料夾...")
        LOG_ARCHIVE_DIR.mkdir(exist_ok=True)

        # 設定時區為台北
        taipei_tz = pytz.timezone("Asia/Taipei")
        # 獲取帶有時區的當前時間
        now_in_taipei = datetime.now(taipei_tz)
        # 格式化為 ISO 8601，並替換 ':' 以利於檔名
        filename = now_in_taipei.isoformat().replace(':', '-') + ".log"

        log_path = LOG_ARCHIVE_DIR / filename

        # 獲取 logger 實例中的所有日誌內容
        log_content = "\n".join(logger.get_log_history())

        log_path.write_text(log_content, encoding='utf-8')
        logger.log("SUCCESS", f"✅ 日誌已成功歸檔至: {log_path}")

    except Exception as e:
        # 在歸檔過程中發生錯誤時，打印到控制台，避免無限循環
        print(f"[CRITICAL] 日誌歸檔失敗: {e}")


def _update_status(shared_state: dict, task: str, error: str = None):
    """一個輔助函式，用於安全地更新共享狀態。"""
    shared_state['current_task'] = task
    shared_state['last_update_time'] = datetime.now().timestamp()
    if error:
        shared_state['error'] = error

def run_main_tasks(shared_state: dict, fast_run: bool = False):
    """
    執行所有主要的背景任務。
    此函式應在一個獨立的執行緒中運行。

    Args:
        shared_state (dict): 用於在執行緒間共享狀態的字典。
        fast_run (bool): 是否啟用快速運行模式。
    """
    try:
        # --- 步驟 1: 安裝依賴 ---
        _update_status(shared_state, "準備安裝核心依賴...")
        logger.log("BATTLE", "=== 開始安裝核心依賴 ===")

        if not fast_run:
            try:
                with open('requirements.txt', 'r', encoding='utf-8') as f:
                    packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except FileNotFoundError:
                logger.log("ERROR", "找不到 requirements.txt 檔案，無法安裝依賴。")
                _update_status(shared_state, "錯誤: 找不到 requirements.txt", "找不到 requirements.txt")
                return

            for i, package in enumerate(packages):
                task_name = f"安裝依賴: {package} ({i+1}/{len(packages)})"
                _update_status(shared_state, task_name)
                logger.log("INFO", f"正在安裝: {package}")

                command = [sys.executable, "-m", "pip", "install", package]

                try:
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        timeout=PIP_INSTALL_TIMEOUT_PER_PACKAGE
                    )
                    if result.returncode != 0:
                        error_message = f"安裝套件 '{package}' 失敗。"
                        logger.log("ERROR", error_message)
                        logger.log("ERROR", f"pip 輸出:\n{result.stderr or result.stdout}")
                        _update_status(shared_state, f"錯誤: {error_message}", error_message)
                        return
                except subprocess.TimeoutExpired:
                    error_message = f"安裝套件 '{package}' 超時 (超過 {PIP_INSTALL_TIMEOUT_PER_PACKAGE} 秒)。"
                    logger.log("ERROR", error_message)
                    _update_status(shared_state, f"錯誤: {error_message}", error_message)
                    return

                logger.log("SUCCESS", f"套件 '{package}' 安裝成功。")
        else:
            _update_status(shared_state, "安裝依賴 (快速運行模式)")
            logger.log("INFO", "快速運行模式：跳過實際的依賴安裝。")
            time.sleep(0.5)

        logger.log("SUCCESS", "✅ 所有核心依賴均已成功安裝。")

        # --- 步驟 2: 執行測試 ---
        _update_status(shared_state, "準備執行整合測試...")
        logger.log("BATTLE", "=== 開始執行整合測試 ===")

        if not fast_run:
            time.sleep(1)
            test_command = [sys.executable, "-m", "pytest"]
            try:
                result = subprocess.run(
                    test_command,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=PYTEST_EXECUTION_TIMEOUT
                )
                if result.returncode != 0:
                    logger.log("WARN", "整合測試未通過。請檢查日誌以獲取詳細資訊。")
                    logger.log("INFO", f"pytest 輸出:\n{result.stdout}")
                else:
                    logger.log("SUCCESS", "✅ 所有整合測試均已通過。")
            except subprocess.TimeoutExpired:
                error_message = f"執行測試超時 (超過 {PYTEST_EXECUTION_TIMEOUT} 秒)。"
                logger.log("ERROR", error_message)
                _update_status(shared_state, f"錯誤: {error_message}", error_message)
                return
        else:
            _update_status(shared_state, "執行測試 (快速運行模式)")
            logger.log("INFO", "快速運行模式：跳過實際的測試執行。")
            time.sleep(0.5)

        _update_status(shared_state, "測試執行完畢。")
        time.sleep(0.2)

        # --- 步驟 3: 模擬主應用程式邏輯 ---
        _update_status(shared_state, "主程式運行中...")
        logger.log("BATTLE", "=== 進入主程式運行階段 ===")

        if not fast_run:
            for i in range(10):
                _update_status(shared_state, f"主程式運行中... (第 {i+1}/10 週期)")
                logger.log("INFO", f"正在處理第 {i+1} 批次的數據...")
                time.sleep(1.5)
        else:
            for i in range(2):
                _update_status(shared_state, f"主程式運行中... (第 {i+1}/2 週期)")
                logger.log("INFO", f"正在處理第 {i+1} 批次的數據 (快速運行模式)...")
                time.sleep(0.2)

        logger.log("SUCCESS", "✅ 主程式所有任務已成功執行完畢。")

        # --- 步驟 4: 啟動並檢查後端伺服器 ---
        server_started = _launch_and_check_server(shared_state, fast_run)

        if server_started:
            # --- 最終狀態 ---
            _update_status(shared_state, "✅ 所有任務完成，後端伺服器運行中。")
            logger.log("BATTLE", "=== 所有任務完成，系統進入監控模式 ===")
            # 保持 worker 存活以示伺服器正在運行
            while not shared_state.get('stop_event', threading.Event()).is_set():
                time.sleep(1)
        else:
            # 如果伺服器啟動失敗，則在此處結束
            logger.log("CRITICAL", "後端伺服器未能啟動，工作執行緒終止。")


    except Exception as e:
        error_message = f"工作執行緒發生未預期的致命錯誤: {e}"
        logger.log("CRITICAL", error_message)
        _update_status(shared_state, "致命錯誤", str(e))
    finally:
        # 執行緒結束時，無論成功或失敗，都歸檔日誌
        _archive_log()
        shared_state['worker_finished'] = True

def _launch_and_check_server(shared_state: dict, fast_run: bool = False) -> bool:
    """
    啟動後端伺服器並透過健康檢查端點驗證其狀態。
    """
    _update_status(shared_state, "準備啟動後端 API 伺服器...")
    logger.log("BATTLE", "=== 開始啟動後端伺服器 ===")

    if fast_run:
        logger.log("INFO", "快速運行模式：跳過實際的伺服器啟動與健康檢查。")
        time.sleep(0.5)
        _update_status(shared_state, "伺服器已啟動 (模擬)")
        return True

    SERVER_HEALTH_CHECK_URL = "http://localhost:8088/api/v1/status"
    SERVER_STARTUP_TIMEOUT = 30
    HEALTH_CHECK_INTERVAL = 2

    import httpx

    server_command = [sys.executable, "scripts/launch.py"]
    process = None
    try:
        process = subprocess.Popen(
            server_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        start_time = time.monotonic()
        while time.monotonic() - start_time < SERVER_STARTUP_TIMEOUT:
            _update_status(shared_state, f"伺服器啟動中... (等待 {int(time.monotonic() - start_time)}s)")
            try:
                response = httpx.get(SERVER_HEALTH_CHECK_URL, timeout=2)
                if response.status_code == 200:
                    logger.log("SUCCESS", f"✅ 後端伺服器健康檢查通過 (URL: {SERVER_HEALTH_CHECK_URL})。")
                    shared_state['server_process'] = process
                    return True
            except httpx.RequestError:
                pass

            time.sleep(HEALTH_CHECK_INTERVAL)

        error_message = f"伺服器啟動超時 (超過 {SERVER_STARTUP_TIMEOUT} 秒)。"
        logger.log("ERROR", error_message)
        _update_status(shared_state, f"錯誤: {error_message}", error_message)
        if process:
            process.terminate()
            process.wait()
        return False

    except Exception as e:
        error_message = f"啟動伺服器時發生例外狀況: {e}"
        logger.log("CRITICAL", error_message)
        _update_status(shared_state, f"錯誤: {error_message}", error_message)
        if process:
            process.terminate()
            process.wait()
        return False
