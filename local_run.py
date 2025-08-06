# -*- coding: utf-8 -*-
# ╔═════════════════════════════════════════════════════════════════════════╗
# ║                                                                         ║
# ║      🎯 local_run.py (V3.0 - 健壯的本地自動化測試器)                      ║
# ║                                                                         ║
# ╠═════════════════════════════════════════════════════════════════════════╣
# ║                                                                         ║
# ║   **目的:**                                                             ║
# ║       作為一個全自動的健康檢查與整合測試腳本。它負責:                     ║
# ║       1. 以標準方式呼叫核心啟動器 `scripts/launch.py`。                 ║
# ║       2. 使用一個強化的「資料庫心跳」看門狗，來驗證後端服務是否不僅啟動， ║
# ║          而且功能正常。                                                 ║
# ║       3. 測試成功後，優雅地關閉所有服務。                               ║
# ║       4. 準備最終的日誌檔案以供分析。                                   ║
# ║                                                                         ║
# ║   **設計哲學:**                                                         ║
# ║       - **日誌優先:** 所有操作都應有清晰、帶時間戳的日誌，以便追蹤。      ║
# ║       - **真實世界模擬:** 看門狗不應只檢查檔案是否存在，而是要模擬客戶端  ║
# ║         行為，直接查詢資料庫，確保服務的真實可用性。                    ║
# ║       - **故障容忍:** 腳本應能處理啟動過程中的臨時性錯誤(如資料庫鎖定)，  ║
# ║         並在最終失敗時提供清晰的錯誤報告。                              ║
# ║                                                                         ║
# ╚═════════════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import time
import shutil
import logging
from datetime import datetime, timezone
import sqlite3
import pytz

# ==============================================================================
#  日誌系統設定 (Logging System Configuration)
# ==============================================================================
# 目的: 設定一個全域的、結構化的日誌系統，取代不規範的 print() 陳述式。
#       這確保了所有輸出都帶有時間戳和嚴重性級別，便於問題排查。
# ------------------------------------------------------------------------------
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)
logger = logging.getLogger('local_run')


# ==============================================================================
#  全域設定與常量 (Global Settings & Constants)
# ==============================================================================
# 目的: 將所有可調整的參數集中管理，方便未來的維護和修改。
# ------------------------------------------------------------------------------
LAUNCHER_SCRIPT = os.path.join("scripts", "launch.py")
DB_PATH = "storage/state.db"
WATCHDOG_TIMEOUT = 10  # 總超時(秒)。根據使用者要求設定。
HEARTBEAT_CHECK_INTERVAL = 2  # 看門狗每次心跳檢查之間的間隔(秒)。
HEARTBEAT_FRESHNESS_THRESHOLD = 15  # 心跳時間戳被視為“新鮮”的最長秒數。超過此值則視為過期。


def print_header(title: str):
    """
    使用 logger 打印一個風格化的標題，用於分隔腳本執行的主要階段。
    """
    logger.info("="*80)
    logger.info(f"🎯 {title}")
    logger.info("="*80)

def run_sync_command(command: list[str], cwd: str = ".", env: dict = None):
    """
    執行一個同步命令，並將其標準輸出和標準錯誤即時串流到日誌中。
    這對於了解子進程的執行情況至關重要。
    """
    logger.info(f"   🔹 執行命令: {' '.join(command)} (於 {cwd})")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', cwd=cwd, env=env
    )
    for line in process.stdout:
        logger.info(f"     [OUTPUT] {line.strip()}")
    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    logger.info(f"   ✅ 命令成功完成。")

def check_database_heartbeat() -> tuple[bool, str]:
    """
    **核心看門狗邏輯**
    直接查詢資料庫，驗證 `last_heartbeat` 時間戳是否在持續更新。
    這是一個真正有效的「心跳檢查」，因為它確認了以下幾點：
    1. 後端服務已啟動。
    2. 資料庫檔案已建立且可存取。
    3. 背景工作執行緒正在運行並成功寫入資料庫。
    """
    if not os.path.exists(DB_PATH):
        logger.debug(f"資料庫檔案尚不存在於: {DB_PATH}")
        return False, "資料庫檔案不存在"

    try:
        # 使用唯讀模式(mode=ro)連接，最大限度地減少對正在運行的服務的干擾。
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        # 查詢關鍵的 'last_heartbeat' 記錄。
        cursor.execute("SELECT timestamp FROM status_updates WHERE key = 'last_heartbeat'")
        result = cursor.fetchone()
        conn.close()

        if not result:
            return False, "在 status_updates 表中找不到 'last_heartbeat' 記錄"

        last_heartbeat_str = result[0]
        # 解析從資料庫讀取的 ISO 8601 格式時間戳。
        last_heartbeat_dt = datetime.fromisoformat(last_heartbeat_str)

        # 獲取當前的 UTC 時間以進行比較。所有時間處理都應在 UTC 中進行以避免時區問題。
        now_utc = datetime.now(pytz.utc)

        time_difference = (now_utc - last_heartbeat_dt).total_seconds()

        if time_difference < HEARTBEAT_FRESHNESS_THRESHOLD:
            logger.info(f"   [看門狗] ✅ 心跳有效！上次心跳在 {time_difference:.2f} 秒前。")
            return True, "心跳正常"
        else:
            # 心跳存在，但時間戳已過期。
            return False, f"心跳已過期！上次心跳在 {time_difference:.2f} 秒前"

    except sqlite3.OperationalError as e:
        # 這是服務啟動初期的一個預期情況，此時資料庫可能被主程序鎖定以進行初始化。
        # 我們將其視為一個暫時性的、非致命的錯誤。
        return False, f"資料庫操作錯誤 (可能正在初始化或被鎖定): {e}"
    except Exception as e:
        logger.error(f"檢查心跳時發生未預期的嚴重錯誤", exc_info=True)
        return False, f"檢查心跳時發生未預期的錯誤: {e}"

def main():
    """腳本的主執行流程。"""
    start_time = time.time()
    server_process = None

    try:
        # --- 步驟 1: 呼叫核心啟動器 ---
        print_header(f"呼叫核心啟動器: {LAUNCHER_SCRIPT}")
        # 使用 Popen 以非阻塞方式啟動伺服器，這樣我們就可以在它運行時進行監控。
        server_process = subprocess.Popen(
            [sys.executable, LAUNCHER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )

        # --- 步驟 2: 看門狗監控 ---
        print_header("啟動看門狗以監控伺服器心跳")
        start_wait = time.monotonic()
        heartbeat_detected = False
        last_reason = ""

        # 這個迴圈是腳本的核心：它在給定的超時時間內持續檢查心跳。
        while time.monotonic() - start_wait < WATCHDOG_TIMEOUT:
            is_alive, reason = check_database_heartbeat()
            if is_alive:
                heartbeat_detected = True
                break

            # 為了避免日誌被重複的相同警告刷屏，只有在失敗原因改變時才打印。
            if reason != last_reason:
                logger.warning(f"   [看門狗] ⚠️ 未偵測到有效心跳: {reason}")
                last_reason = reason

            # 在等待的間隙，打印來自伺服器進程的即時輸出，這對於除錯至關重要。
            try:
                line = server_process.stdout.readline()
                if line:
                    logger.info(f"     [SERVER] {line.strip()}")
            except (IOError, ValueError):
                # 當子進程終止時，readline 可能會引發異常，這是正常的。
                pass

            time.sleep(HEARTBEAT_CHECK_INTERVAL)

        if not heartbeat_detected:
            # 如果在整個超時時間內都沒有檢測到有效心跳，則測試失敗。
            raise RuntimeError(f"看門狗超時！在 {WATCHDOG_TIMEOUT} 秒內未偵測到有效心跳。最後原因: {last_reason}")

        # --- 步驟 3: 成功後，優雅地關閉伺服器 ---
        print_header("測試成功，正在終止伺服器")
        server_process.terminate() # 發送 SIGTERM 訊號，請求優雅關閉。
        try:
            server_process.wait(timeout=10) # 給予 10 秒的寬限期。
            logger.info("✅ 伺服器已成功終止。")
        except subprocess.TimeoutExpired:
            # 如果伺服器未能優雅關閉，則強制終止。
            logger.warning("⚠️ 伺服器終止超時，強制中斷 (kill)。")
            server_process.kill()

        # --- 步驟 4: 準備報告 ---
        print_header("準備日誌報告")
        # 將最終的狀態資料庫重新命名，以便進行存檔或後續分析。
        db_renamed_path = "logs.sqlite"
        if os.path.exists(DB_PATH):
            shutil.move(DB_PATH, db_renamed_path)
            logger.info(f"✅ 資料庫已從 '{DB_PATH}' 重命名為 '{db_renamed_path}' 以供分析。")
        else:
            logger.warning(f"⚠️ 找不到資料庫檔案 '{DB_PATH}'，無法生成報告。")
            # 建立一個空的日誌檔案以確保下游腳本的一致性。
            open(db_renamed_path, 'a').close()

    except Exception as e:
        # 全域的異常捕獲，確保任何失敗都會被記錄下來。
        logger.error(f"❌ local_run 在執行期間遭遇無法恢復的錯誤。", exc_info=True)
        if server_process and server_process.poll() is None:
            # 確保即使發生錯誤，子進程也不會被遺棄。
            logger.info("正在終止任何殘留的伺服器進程...")
            server_process.kill()
            logger.info("伺服器進程已終止。")
        sys.exit(1)
    finally:
        # 無論成功或失敗，都打印最終的執行時間。
        end_time = time.time()
        logger.info("="*80)
        logger.info(f"🏁 local_run 流程結束，總耗時: {end_time - start_time:.2f} 秒。")
        logger.info("="*80)

if __name__ == "__main__":
    main()
