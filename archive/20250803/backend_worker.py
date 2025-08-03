# -*- coding: utf-8 -*-
# 版本：V30 - 雙模態架構：資料庫驅動工作者
# 目的：作為一個獨立的後端工作程序，負責執行核心任務並將狀態寫入資料庫。
import sys
import os
import time
import threading
import argparse
import json
from datetime import datetime
import psutil
import pytz

# 確保 src 目錄在 Python 路徑中，以便能正確匯入 phoenix_core
# 假設此腳本總是從專案根目錄執行，或者由一個設定好環境的啟動器執行
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.phoenix_core.database import db_manager

# --- 全域控制旗標 ---
stop_event = threading.Event()

def print_log(message, level="INFO"):
    """
    一個簡單的日誌函式，將日誌打印到 stdout 並寫入資料庫。
    """
    timestamp = datetime.now(pytz.timezone("Asia/Taipei")).strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)
    try:
        # 假設 db_manager 已經被主執行緒初始化
        db_manager.write_log(level, message, source="backend_worker")
    except Exception as e:
        print(f"[DB Log Error] 無法寫入日誌到資料庫: {e}")

from src.phoenix_core.utils.resource_monitor import log_system_resources

def hardware_monitor_thread(interval: int):
    """
    一個專門監控硬體資源的執行緒，現在委託給 resource_monitor 模組處理。
    """
    print_log("🟢 硬體監控執行緒已啟動。")
    while not stop_event.is_set():
        try:
            # 呼叫統一的資源記錄函數
            log_system_resources()
            print_log(f"💻 硬體狀態已記錄到資料庫。", level="PERF")

        except Exception as e:
            print_log(f"🔴 硬體監控執行緒發生錯誤: {e}", level="ERROR")

        # 等待指定的間隔，同時也檢查停止訊號
        stop_event.wait(interval)
    print_log("🔴 硬體監控執行緒已停止。")


def core_logic_thread(config: dict):
    """
    一個模擬執行核心業務邏輯的執行緒。
    """
    print_log("🟢 核心業務邏輯執行緒已啟動。")
    db_manager.write_status_update("current_stage", "核心邏輯啟動")

    try:
        # 模擬一些啟動工作
        print_log("⏳ 正在執行啟動任務...")
        time.sleep(5)
        db_manager.write_status_update("current_stage", "啟動任務完成")
        print_log("✅ 啟動任務完成。")

        # 模擬一個長時間運行的任務
        counter = 0
        while not stop_event.is_set():
            counter += 1
            message = f"核心任務執行中，計數: {counter}"
            print_log(message)
            db_manager.write_status_update("core_logic_status", message)

            if counter >= 10:
                print_log("🎉 核心業務邏輯執行緒已完成其任務。")
                db_manager.write_status_update("current_stage", "核心邏輯完成")
                break

            stop_event.wait(2)

    except Exception as e:
        error_message = f"🔴 核心業務邏輯執行緒發生錯誤: {e}"
        print_log(error_message, level="CRITICAL")
        db_manager.write_status_update("current_stage", "核心邏輯失敗")
        db_manager.write_status_update("error_message", error_message)

    print_log("🔴 核心業務邏輯執行緒已停止。")


def main():
    parser = argparse.ArgumentParser(description="Phoenix Heart Backend Worker (V30)")
    parser.add_argument("--config", type=str, required=True, help="Path to the config.json file.")
    args = parser.parse_args()

    print_log("🚀 後端工作者 (Backend Worker) V30 啟動...")

    # --- 讀取設定檔 ---
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
        print_log(f"✅ 成功讀取設定檔: {args.config}")
    except Exception as e:
        print_log(f"❌ 無法讀取設定檔: {e}", level="CRITICAL")
        sys.exit(1)

    # --- 初始化資料庫 ---
    # 這是主執行緒，db_manager 會在此處被首次初始化
    try:
        db_manager.write_status_update("backend_status", "starting")
        print_log("✅ 資料庫管理器初始化成功。")
    except Exception as e:
        print_log(f"❌ 資料庫初始化失敗: {e}", level="CRITICAL")
        sys.exit(1)


    # --- 啟動背景執行緒 ---
    threads = [
        threading.Thread(target=hardware_monitor_thread, args=(5,)),
        threading.Thread(target=core_logic_thread, args=(config,))
    ]

    for t in threads:
        t.daemon = True
        t.start()

    db_manager.write_status_update("backend_status", "running")
    print_log("✅ 所有背景執行緒已啟動。後端工作者正在運行...")
    print_log("   使用 Ctrl+C 來停止服務。")

    # --- 主執行緒等待 ---
    try:
        # 主執行緒保持運行，直到所有非 daemon 執行緒結束或被中斷
        while any(t.is_alive() for t in threads):
            time.sleep(1)

    except KeyboardInterrupt:
        print_log("\n🛑 收到手動中斷 (Ctrl+C)，正在優雅關閉...")
        db_manager.write_status_update("backend_status", "stopping")
        stop_event.set()

    # 等待所有執行緒結束
    for t in threads:
        t.join(timeout=5)

    db_manager.write_status_update("backend_status", "stopped")
    print_log("✅ 所有執行緒已成功停止。後端工作者已關閉。")


if __name__ == "__main__":
    main()
