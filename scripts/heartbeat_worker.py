# -*- coding: utf-8 -*-
# 檔案: scripts/heartbeat_worker.py
# 說明: 核心背景任務管理器。
#       這是所有非 API 服務的唯一入口點。它啟動一個 asyncio 事件循環，
#       並在其中運行所有必要的背景任務，例如：
#       - 定期心跳
#       - 音訊轉錄任務輪詢
#       - Prometheus 指標抓取
#       等等。

import asyncio
import sys
from pathlib import Path

def main():
    """
    主執行函數：設定路徑，初始化任務，並永久運行事件循環。
    """
    # --- 步驟 1: 設定路徑 ---
    # 確保我們可以從 src 目錄導入模組。
    # 這是至關重要的一步，確保所有子模組都能被正確找到。
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # --- 步驟 2: 導入核心服務 ---
    # 在設定好路徑後，才能安全地導入我們的模組。
    try:
        from src.phoenix_core.background.worker import start_background_tasks
        from src.phoenix_core.database import db_manager
        from src.phoenix_core.utils.logger import logger
    except ImportError as e:
        # 如果這裡發生錯誤，說明基礎結構有問題，直接退出。
        print(f"FATAL: 核心模組導入失敗: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 步驟 3: 初始化並運行事件循環 ---
    print("核心背景任務管理器啟動...")

    async def run_worker():
        # 初始化資料庫連接
        try:
            # 必須調用 async_initialize 而不是 initialize
            await db_manager.async_initialize()
            await logger.log("INFO", "資料庫管理器初始化成功。", source="CoreWorker")
        except Exception as e:
            # 使用 print 是因為 logger 可能還沒完全初始化
            print(f"CRITICAL: 資料庫初始化失敗，背景工作無法啟動: {e}", file=sys.stderr)
            return # 無法繼續

        # 啟動所有在 background/worker.py 中定義的背景任務
        start_background_tasks()

        await logger.log("SUCCESS", "所有背景任務已啟動並在事件循環中運行。", source="CoreWorker")

        # 保持事件循環永久運行
        # 我們可以加入一個 dummy future 來等待，這樣可以捕獲 KeyboardInterrupt
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            await logger.log("INFO", "背景任務管理器收到取消訊號。", source="CoreWorker")
        finally:
            # db_manager 沒有 close() 方法，但有 close_connection()
            # 在這個上下文中，我們不需要手動關閉，因為它是 thread-local 的
            # 並且進程結束時會自動清理。
            await logger.log("INFO", "背景任務管理器正在關閉。", source="CoreWorker")


    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\n收到使用者中斷 (Ctrl+C)。正在關閉背景任務管理器...")
    except Exception as e:
        # 捕獲任何未預料的頂層錯誤
        print(f"FATAL: 背景任務管理器遭遇無法恢復的錯誤: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
