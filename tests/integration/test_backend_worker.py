# -*- coding: utf-8 -*-
# 檔案: tests/integration/test_backend_worker.py
# V30 整合測試: 驗證後端工作者與資料庫寫入

import sys
import os
import subprocess
import time
import pytest
import sqlite3
import threading
from pathlib import Path

# --- 測試設定 ---
RUNNER_SCRIPT = Path(__file__).parent.parent.parent / "run" / "colab_runner.py"
# V30 測試架構：直接在專案根目錄執行，不再創建和清理 WEB1 子目錄
DB_FILE = Path(__file__).parent.parent.parent / "state.db"
RUN_TIMEOUT = 300  # 大幅延長超時時間 (5分鐘)，以應對 CI 環境中緩慢的首次依賴安裝

@pytest.fixture(scope="module")
def setup_and_run_backend():
    """
    一個執行完整後端流程的 fixture。
    1. 在背景執行 colab_runner.py。
    2. 等待資料庫檔案被建立。
    3. 在測試結束後，清理程序和資料庫檔案。
    """
    # --- 前置清理 ---
    if DB_FILE.exists():
        DB_FILE.unlink()

    if not RUNNER_SCRIPT.exists():
        pytest.fail(f"測試目標腳本不存在: {RUNNER_SCRIPT}")

    # --- 在背景啟動 runner ---
    print(f"\n🚀 正在背景啟動測試目標: {RUNNER_SCRIPT}")
    # 在本地模式下，runner 會在前台打印日誌，所以我們用 Popen 在背景運行它
    process = subprocess.Popen(
        [sys.executable, str(RUNNER_SCRIPT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )

    # --- 等待資料庫檔案建立 ---
    start_time = time.time()
    try:
        while not DB_FILE.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(
                    f"Runner 程序提前終止，資料庫檔案未建立。\n"
                    f"STDOUT: {stdout}\nSTDERR: {stderr}"
                )
            if time.time() - start_time > RUN_TIMEOUT:
                stdout, stderr = process.communicate()
                process.kill()
                pytest.fail(
                    f"執行 runner 超時 ({RUN_TIMEOUT}s)，資料庫檔案未建立。\n"
                    f"STDOUT: {stdout}\nSTDERR: {stderr}"
                )
            time.sleep(1)

        print(f"✅ 資料庫檔案在 {time.time() - start_time:.2f} 秒後建立: {DB_FILE}")

        # 再給予幾秒鐘讓 worker 執行緒寫入一些數據
        print("⏳ 等待後端工作者寫入數據...")
        time.sleep(15)

        yield # 測試將在此處執行

    finally:
        # --- 清理 ---
        print("\n🧹 正在清理測試環境...")
        if process.poll() is None:
            print("   終止 runner 程序...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        if DB_FILE.exists():
            print(f"   刪除資料庫檔案: {DB_FILE}")
            DB_FILE.unlink()

        print("✅ 清理完成。")


def test_database_is_written(setup_and_run_backend):
    """
    驗證後端工作者是否成功將狀態寫入資料庫。
    """
    print("\n🧪 開始驗證資料庫內容...")
    assert DB_FILE.exists(), "斷言失敗: 資料庫檔案不存在。"

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 驗證 1: status 表是否被寫入
        cursor.execute("SELECT value FROM status WHERE key = 'backend_status'")
        result = cursor.fetchone()
        assert result is not None, "斷言失敗: 'backend_status' 未在資料庫中找到。"
        assert result[0] in ["running", "stopping"], f"斷言失敗: 'backend_status' 狀態不正確 ({result[0]})"
        print(f"   ✅ 狀態 'backend_status' 驗證成功 (值: {result[0]})")

        # 驗證 2: 檢查一個由執行緒寫入的具體狀態
        cursor.execute("SELECT value FROM status WHERE key = 'cpu_usage'")
        result = cursor.fetchone()
        assert result is not None, "斷言失敗: 'cpu_usage' 未在資料庫中找到。"
        cpu_val = float(result[0])
        assert 0.0 <= cpu_val <= 100.0, f"斷言失敗: 'cpu_usage' 值不合理 ({cpu_val})。"
        print(f"   ✅ 狀態 'cpu_usage' 驗證成功 (值: {cpu_val})")

        # 驗證 3: 檢查 logs 表是否被寫入
        cursor.execute("SELECT COUNT(*) FROM logs")
        log_count = cursor.fetchone()[0]
        assert log_count > 0, "斷言失敗: logs 表中沒有任何日誌。"
        print(f"   ✅ 'logs' 表已寫入 {log_count} 條日誌。")

        conn.close()

    except sqlite3.Error as e:
        pytest.fail(f"讀取資料庫時發生錯誤: {e}")

    print("✅ 資料庫內容驗證成功！")
