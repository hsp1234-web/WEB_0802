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
# 修正：直接測試後端工作者，而不是 Colab 啟動器
WORKER_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "backend_worker.py"
DB_FILE = Path(__file__).parent.parent.parent / "state.db"
CONFIG_FILE = Path(__file__).parent.parent.parent / "test_worker_config.json"
RUN_TIMEOUT = 300

@pytest.fixture(scope="module")
def setup_and_run_backend():
    """
    一個執行完整後端流程的 fixture。
    1. 建立一個臨時設定檔。
    2. 在背景執行 backend_worker.py。
    3. 等待資料庫檔案被建立。
    4. 在測試結束後，清理程序、設定檔和資料庫檔案。
    """
    # --- 前置清理 ---
    for f in [DB_FILE, CONFIG_FILE]:
        if f.exists():
            f.unlink()

    # --- 建立臨時設定檔 ---
    with open(CONFIG_FILE, "w") as f:
        f.write("{}") # backend_worker.py 需要一個有效的 JSON 檔案

    if not WORKER_SCRIPT.exists():
        pytest.fail(f"測試目標腳本不存在: {WORKER_SCRIPT}")

    # --- 在背景啟動 worker ---
    print(f"\n🚀 正在背景啟動測試目標: {WORKER_SCRIPT}")
    command = [sys.executable, str(WORKER_SCRIPT), "--config", str(CONFIG_FILE)]
    process = subprocess.Popen(
        command,
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
                    f"Worker 程序提前終止，資料庫檔案未建立。\n"
                    f"STDOUT: {stdout}\nSTDERR: {stderr}"
                )
            if time.time() - start_time > RUN_TIMEOUT:
                stdout, stderr = process.communicate()
                process.kill()
                pytest.fail(
                    f"執行 worker 超時 ({RUN_TIMEOUT}s)，資料庫檔案未建立。\n"
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
            print("   終止 worker 程序...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        for f in [DB_FILE, CONFIG_FILE]:
            if f.exists():
                print(f"   刪除檔案: {f}")
                f.unlink()

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

        # 驗證 1: status_updates 表是否被寫入
        cursor.execute("SELECT value FROM status_updates WHERE key = 'backend_status'")
        result = cursor.fetchone()
        assert result is not None, "斷言失敗: 'backend_status' 未在資料庫中找到。"
        assert result[0] in ["running", "stopping"], f"斷言失敗: 'backend_status' 狀態不正確 ({result[0]})"
        print(f"   ✅ 狀態 'backend_status' 驗證成功 (值: {result[0]})")

        # 驗證 2: 檢查 hardware_stats 表是否被寫入
        cursor.execute("SELECT cpu_usage, memory_usage, disk_usage FROM hardware_stats ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        assert result is not None, "斷言失敗: 未在 'hardware_stats' 表中找到任何紀錄。"
        cpu, mem, disk = result
        assert 0.0 <= cpu <= 100.0, f"斷言失敗: 'cpu_usage' 值不合理 ({cpu})。"
        assert 0.0 <= mem <= 100.0, f"斷言失敗: 'memory_usage' 值不合理 ({mem})。"
        assert 0.0 <= disk <= 100.0, f"斷言失敗: 'disk_usage' 值不合理 ({disk})。"
        print(f"   ✅ 'hardware_stats' 表驗證成功 (CPU: {cpu}%, Mem: {mem}%, Disk: {disk}%)")

        # 驗證 3: 檢查 logs 表是否被寫入
        cursor.execute("SELECT COUNT(*) FROM logs")
        log_count = cursor.fetchone()[0]
        assert log_count > 0, "斷言失敗: logs 表中沒有任何日誌。"
        print(f"   ✅ 'logs' 表已寫入 {log_count} 條日誌。")

        conn.close()

    except sqlite3.Error as e:
        pytest.fail(f"讀取資料庫時發生錯誤: {e}")

    print("✅ 資料庫內容驗證成功！")
