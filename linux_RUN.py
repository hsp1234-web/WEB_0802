# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║         🚀 鳳凰之心 Linux 獨立儀表板 (v1.0)                        ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 提供一個獨立、美觀且資訊豐富的終端儀表板，用於監控      ║
# ║           應用程式的安裝、測試與執行過程。                         ║
# ║   - 架構: 多執行緒 (UI, Worker) + SQLite 日誌 + ANSI 介面          ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import threading
import time
import sys
from datetime import datetime

import os

# 將專案根目錄加入 Python 的搜尋路徑，以允許 'from src...' 匯入
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# --- 核心模組匯入 ---
# 確保 src 目錄在 Python 的搜尋路徑中
# 這使得無論從哪裡執行此腳本，都能找到 phoenix_core 模組
try:
    from src.phoenix_core.utils.logger import logger
    # from src.phoenix_core.utils.display import DisplayManager # 已停用
    from src.phoenix_core.utils.worker import run_main_tasks
except ImportError as e:
    print(f"錯誤: 無法匯入核心模組 ({e})。請確保 `src` 目錄與此腳本位於同一專案根目錄下。")
    sys.exit(1)


# --- 全域設定 ---
WATCHDOG_TIMEOUT_SECONDS = 10  # 如果任務在 10 秒內無任何進展，則視為超時

import argparse

def main():
    """
    主應用程式函數。
    """
    # --- 參數解析 ---
    parser = argparse.ArgumentParser(description="鳳凰之心 Linux 獨立儀表板")
    parser.add_argument(
        '--fast-run',
        action='store_true',
        help='啟用快速運行模式，跳過實際的耗時操作，用於測試。'
    )
    args = parser.parse_args()

    # 1. 初始化共享狀態
    # 這個字典將在主執行緒、顯示執行緒和工作執行緒之間共享
    stop_event = threading.Event()
    shared_state = {
        'current_task': '系統初始化中...',
        'last_update_time': datetime.now().timestamp(),
        'error': None,
        'worker_finished': False,
        'server_process': None,
        'stop_event': stop_event,
    }

    # 2. 初始化日誌
    logger.log("BATTLE", "=== 鳳凰之心純日誌系統啟動 ===")
    # display = DisplayManager(shared_state, log_lines=15) # 已停用

    # 3. 建立並準備工作執行緒
    worker_thread = threading.Thread(
        target=run_main_tasks,
        args=(shared_state, args.fast_run), # 將 fast_run 旗標傳遞給 worker
        daemon=True
    )

    # 4. 啟動工作執行緒
    # display.start() # 已停用
    worker_thread.start()

    try:
        # 5. 主執行緒的「看門狗」與簡易狀態回報迴圈
        logger.log("INFO", "主執行緒進入監控模式...")
        while worker_thread.is_alive():
            # 檢查工作執行緒是否卡住
            now = datetime.now().timestamp()
            time_since_last_update = now - shared_state.get('last_update_time', now)

            if time_since_last_update > WATCHDOG_TIMEOUT_SECONDS:
                error_message = f"看門狗超時: 背景任務超過 {WATCHDOG_TIMEOUT_SECONDS} 秒無回應。"
                logger.log("CRITICAL", error_message)
                shared_state['error'] = error_message
                break  # 偵測到超時，跳出迴圈以關閉程式

            # 每 2 秒打印一次存活心跳和當前任務狀態
            logger.log("INFO", f"[主線程監控] 背景任務執行中: {shared_state.get('current_task', 'N/A')}")
            worker_thread.join(timeout=2.0)  # 等待 2 秒或直到執行緒結束

    except KeyboardInterrupt:
        logger.log("WARN", "偵測到使用者手動中斷 (Ctrl+C)。")
        shared_state['current_task'] = "使用者請求關機..."
        stop_event.set() # 通知 worker 的監控迴圈停止

    except Exception as e:
        logger.log("CRITICAL", f"主執行緒發生未預期的致命錯誤: {e}")
        shared_state['error'] = f"主執行緒致命錯誤: {e}"

    finally:
        # 6. 優雅關機程序
        logger.log("BATTLE", "=== 系統正在關機 ===")

        # 停止背景伺服器 (如果它正在運行)
        server_process = shared_state.get('server_process')
        if server_process and server_process.poll() is None:
            logger.log("INFO", f"正在關閉後端伺服器 (PID: {server_process.pid})...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                logger.log("SUCCESS", "後端伺服器已成功關閉。")
            except subprocess.TimeoutExpired:
                logger.log("WARN", "後端伺服器在 5 秒內未回應終止信號，將強制終止。")
                server_process.kill()

        # 確保工作執行緒已結束
        if worker_thread.is_alive():
            logger.log("WARN", "工作執行緒仍在運行，等待其結束...")
            stop_event.set() # 再次確保事件被設定
            worker_thread.join(timeout=2)

        # 停止顯示執行緒
        # display.stop() # 已停用

        # 確保在所有操作完成後，再進行日誌歸檔
        time.sleep(0.5) # 給顯示執行緒一點時間來打印最後的訊息

        print("\n" * 2) # 換行，避免歸檔訊息覆蓋儀表板
        logger.log("INFO", "正在將日誌歸檔到文字檔案...")
        archive_path = logger.archive_logs_to_file(shared_state)

        if archive_path:
            print(f"日誌已成功歸檔至: {archive_path}")
        else:
            print("日誌歸檔失敗。")

        logger.close()
        print("鳳凰之心系統已安全關閉。")


if __name__ == "__main__":
    # 檢查是否在 Pytest 環境中運行
    # 如果是，則不執行 main()，避免在測試匯入時自動運行
    if "pytest" not in sys.modules:
        main()
