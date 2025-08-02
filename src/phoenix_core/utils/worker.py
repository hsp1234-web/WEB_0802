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

from src.phoenix_core.utils.logger import logger

def _update_status(shared_state: dict, task: str, error: str = None):
    """一個輔助函式，用於安全地更新共享狀態。"""
    shared_state['current_task'] = task
    shared_state['last_update_time'] = datetime.now().timestamp()
    if error:
        shared_state['error'] = error

def run_main_tasks(shared_state: dict):
    """
    執行所有主要的背景任務。
    此函式應在一個獨立的執行緒中運行。

    Args:
        shared_state (dict): 用於在執行緒間共享狀態的字典。
    """
    try:
        # --- 步驟 1: 安裝依賴 ---
        _update_status(shared_state, "準備安裝核心依賴...")
        logger.log("BATTLE", "=== 開始安裝核心依賴 ===")

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

            # 使用 sys.executable 確保我們用的是當前 Python 環境的 pip
            command = [sys.executable, "-m", "pip", "install", package]

            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                error_message = f"安裝套件 '{package}' 失敗。"
                logger.log("ERROR", error_message)
                logger.log("ERROR", f"pip 輸出:\n{result.stderr or result.stdout}")
                _update_status(shared_state, f"錯誤: {error_message}", error_message)
                return # 中止後續任務

            logger.log("SUCCESS", f"套件 '{package}' 安裝成功。")

        logger.log("SUCCESS", "✅ 所有核心依賴均已成功安裝。")

        # --- 步驟 2: 執行測試 ---
        _update_status(shared_state, "準備執行整合測試...")
        logger.log("BATTLE", "=== 開始執行整合測試 ===")
        time.sleep(1) # 讓使用者能看到狀態更新

        test_command = [sys.executable, "-m", "pytest"]

        result = subprocess.run(test_command, capture_output=True, text=True, encoding='utf-8')

        if result.returncode != 0:
            # 測試失敗通常不應中止主程式，但需要記錄為警告
            logger.log("WARN", "整合測試未通過。請檢查日誌以獲取詳細資訊。")
            logger.log("INFO", f"pytest 輸出:\n{result.stdout}")
        else:
            logger.log("SUCCESS", "✅ 所有整合測試均已通過。")

        _update_status(shared_state, "測試執行完畢。")
        time.sleep(1)

        # --- 步驟 3: 模擬主應用程式邏輯 ---
        _update_status(shared_state, "主程式運行中...")
        logger.log("BATTLE", "=== 進入主程式運行階段 ===")

        for i in range(10):
            _update_status(shared_state, f"主程式運行中... (第 {i+1}/10 週期)")
            logger.log("INFO", f"正在處理第 {i+1} 批次的數據...")
            time.sleep(1.5) # 模擬耗時操作

        logger.log("SUCCESS", "✅ 主程式所有任務已成功執行完畢。")

        # --- 最終狀態 ---
        _update_status(shared_state, "所有任務完成，系統待命中。")
        logger.log("BATTLE", "=== 所有任務完成 ===")

    except Exception as e:
        error_message = f"工作執行緒發生未預期的致命錯誤: {e}"
        logger.log("CRITICAL", error_message)
        _update_status(shared_state, "致命錯誤", str(e))
    finally:
        # 可以在此處設定一個旗標，表示工作執行緒已結束
        shared_state['worker_finished'] = True
