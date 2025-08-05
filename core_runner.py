# -*- coding: utf-8 -*-
# 檔案: core_runner.py
# 說明: 核心應用程式執行器。
#      此腳本應由 venv 中的 Python 解譯器執行，
#      以確保所有依賴都已安裝。

import sys
import os
import asyncio
import time
from datetime import datetime
import uvicorn

# 將 'src' 目錄添加到 Python 路徑中
sys.path.insert(0, os.path.abspath('src'))

from phoenix_core.main import app
from phoenix_core.database import db_manager
from phoenix_core.watchdog import HEARTBEAT_KEY

# --- 全域設定 (從 local_run.py 複製) ---
WATCHDOG_TIMEOUT = 20
HEARTBEAT_CHECK_INTERVAL = 1

def get_timestamp():
    """獲取當前時間戳，用於日誌。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    print("\n" + "="*80)
    print(f"🚀 {get_timestamp()} - {title}")
    print("="*80)

async def watchdog_and_closer(server) -> bool:
    """
    【Asyncio 原生看門狗】
    監控心跳，成功後或超時後關閉伺服器。
    """
    start_time = time.monotonic()
    print_header(f"看門狗已啟動 (超時設定: {WATCHDOG_TIMEOUT} 秒)")

    while time.monotonic() - start_time < WATCHDOG_TIMEOUT:
        print(f"   [看門狗] 正在檢查心跳...")
        try:
            heartbeat_value = await asyncio.to_thread(db_manager.get_status, HEARTBEAT_KEY)
            if heartbeat_value:
                print(f"   [看門狗] ✅ 成功偵測到心跳！值: {heartbeat_value}")
                print("   [看門狗] 測試通過。等待 5 秒觀察期...")
                await asyncio.sleep(5)
                server.should_exit = True
                print("   [看門狗] 已發出關閉信號。")
                return True
            else:
                print(f"   [看門狗] ⚠️ 未找到心跳值，將在 {HEARTBEAT_CHECK_INTERVAL} 秒後重試...")
        except Exception as e:
            print(f"   [看門狗] ❌ 檢查心跳時發生錯誤: {e}", file=sys.stderr)
        await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)

    print(f"   [看門狗] ❌ 超時！在 {WATCHDOG_TIMEOUT} 秒內未偵測到有效心跳。", file=sys.stderr)
    server.should_exit = True
    return False

async def main_async():
    """
    【異步主函式】
    協調 Uvicorn 伺服器和看門狗的啟動與關閉。
    """
    print_header("步驟 4: 以程式化方式啟動核心應用程式")

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        lifespan="on"
    )
    server = uvicorn.Server(config)

    server_task = asyncio.create_task(server.serve())
    watchdog_task = asyncio.create_task(watchdog_and_closer(server))

    done, pending = await asyncio.wait(
        [server_task, watchdog_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    watchdog_result = False
    if watchdog_task in done:
        watchdog_result = watchdog_task.result()

    for task in pending:
        task.cancel()

    await asyncio.gather(*pending, return_exceptions=True)

    if not watchdog_result:
        raise RuntimeError("看門狗超時，測試失敗。")

    print("✅ 伺服器已優雅地關閉。")

if __name__ == "__main__":
    try:
        # 將 'src' 目錄添加到 Python 路徑中，以解決模組導入問題
        # 這確保了即使在 venv 啟用前，腳本也能找到 'phoenix_core' 模組
        sys.path.insert(0, os.path.abspath('src'))
        asyncio.run(main_async())
        print("✅ 核心應用程式測試運行已完成。")
    except Exception as e:
        print(f"\n❌ 核心執行階段發生錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
