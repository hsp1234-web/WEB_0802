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
    from src.phoenix_core.utils.display import DisplayManager
    from src.phoenix_core.utils.worker import run_main_tasks
except ImportError as e:
    print(f"錯誤: 無法匯入核心模組 ({e})。請確保 `src` 目錄與此腳本位於同一專案根目錄下。")
    sys.exit(1)


# --- 全域設定 ---
WATCHDOG_TIMEOUT_SECONDS = 60  # 如果任務在 60 秒內無任何進展，則視為超時

def main():
    """
    主應用程式函數。
    """
    # 1. 初始化共享狀態
    # 這個字典將在主執行緒、顯示執行緒和工作執行緒之間共享
    shared_state = {
        'current_task': '系統初始化中...',
        'last_update_time': datetime.now().timestamp(),
        'error': None,
        'worker_finished': False,
    }

    # 2. 初始化日誌和顯示管理器
    logger.log("BATTLE", "=== 鳳凰之心儀表板系統啟動 ===")
    display = DisplayManager(shared_state, log_lines=15)

    # 3. 建立並準備工作執行緒
    worker_thread = threading.Thread(
        target=run_main_tasks,
        args=(shared_state,),
        daemon=True
    )

    # 4. 啟動顯示和工作執行緒
    display.start()
    worker_thread.start()

    try:
        # 5. 主執行緒的「看門狗」迴圈
        while worker_thread.is_alive():
            # 檢查工作執行緒是否卡住
            now = datetime.now().timestamp()
            time_since_last_update = now - shared_state.get('last_update_time', now)

            if time_since_last_update > WATCHDOG_TIMEOUT_SECONDS:
                error_message = f"看門狗超時: 任務超過 {WATCHDOG_TIMEOUT_SECONDS} 秒無回應。"
                logger.log("CRITICAL", error_message)
                shared_state['error'] = error_message
                break # 偵測到超時，跳出迴圈以關閉程式

            worker_thread.join(timeout=1.0) # 每秒檢查一次

    except KeyboardInterrupt:
        logger.log("WARN", "偵測到使用者手動中斷 (Ctrl+C)。")
        shared_state['current_task'] = "使用者請求關機..."
        # 不需要手動停止 worker，讓它自然結束或在 finally 中處理
        # display.stop() 會在 finally 中被呼叫

    except Exception as e:
        logger.log("CRITICAL", f"主執行緒發生未預期的致命錯誤: {e}")
        shared_state['error'] = f"主執行緒致命錯誤: {e}"

    finally:
        # 6. 優雅關機程序
        logger.log("BATTLE", "=== 系統正在關機 ===")

        # 確保工作執行緒已結束
        if worker_thread.is_alive():
            # 這通常只會在超時或錯誤時發生
            logger.log("WARN", "工作執行緒仍在運行，等待其結束...")
            # 在此我們不強制終止，因為 worker 可能正在寫入重要數據
            # 在真實應用中，可能需要更複雜的信號機制
            worker_thread.join(timeout=5)

        # 停止顯示執行緒
        display.stop()

        # 確保在所有操作完成後，再進行日誌歸檔
        time.sleep(0.5) # 給顯示執行緒一點時間來打印最後的訊息

        print("\n" * 2) # 換行，避免歸檔訊息覆蓋儀表板
        logger.log("INFO", "正在將日誌歸檔到文字檔案...")
        archive_path = logger.archive_logs_to_file()

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
