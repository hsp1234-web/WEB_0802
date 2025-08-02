# -*- coding: utf-8 -*-
"""
端對端測試 (End-to-End Test) for linux_RUN.py
"""
import subprocess
import sys
import time
import os
import signal
import pytest

# --- 測試設定 ---
# 專案根目錄，假設此測試檔案位於 project_root/tests/e2e/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNNER_SCRIPT = os.path.join(PROJECT_ROOT, "linux_RUN.py")
LOG_DB = os.path.join(PROJECT_ROOT, "logs.sqlite")
LOG_ARCHIVE_DIR = os.path.join(PROJECT_ROOT, "作戰日誌歸檔")


@pytest.fixture(scope="module", autouse=True)
def cleanup_logs():
    """
    一個在測試前後清理日誌檔案的 fixture。
    `autouse=True` 確保它會為此模組中的所有測試自動運行。
    """
    # --- 測試前清理 ---
    if os.path.exists(LOG_DB):
        os.remove(LOG_DB)
    if os.path.exists(LOG_ARCHIVE_DIR):
        import shutil
        shutil.rmtree(LOG_ARCHIVE_DIR)

    yield # 執行測試

    # --- 測試後清理 (可選，但保持環境乾淨是個好習慣) ---
    if os.path.exists(LOG_DB):
        os.remove(LOG_DB)
    if os.path.exists(LOG_ARCHIVE_DIR):
        import shutil
        shutil.rmtree(LOG_ARCHIVE_DIR)


def test_runner_lifecycle_and_graceful_shutdown():
    """
    測試 linux_RUN.py 的完整生命週期：
    1. 使用 --fast-run 模式啟動。
    2. 驗證儀表板是否正常輸出。
    3. 發送 SIGINT (Ctrl+C) 信號。
    4. 驗證程式是否能優雅關機。
    5. 驗證日誌是否已正確生成和歸檔。
    """
    # 確保 runner 腳本存在
    assert os.path.exists(RUNNER_SCRIPT), f"測試目標 {RUNNER_SCRIPT} 不存在。"

    command = [sys.executable, RUNNER_SCRIPT, "--fast-run"]

    # 使用 Popen 在背景啟動程序
    # `preexec_fn=os.setsid` 確保我們可以向整個程序組發送信號，
    # 這在某些 shell 環境下對於確保 Ctrl+C 能被正確傳遞很重要。
    # 注意：`preexec_fn` 在 Windows 上不可用。
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        preexec_fn=os.setsid if sys.platform != "win32" else None
    )

    try:
        # 讓程式運行幾秒鐘以產生輸出
        time.sleep(3)

        # --- 驗證程序仍在運行 ---
        assert process.poll() is None, "程序在測試期間意外提前終止。"

        # --- 向程序發送 SIGINT (Ctrl+C) ---
        if sys.platform != "win32":
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
        else:
            process.send_signal(signal.CTRL_C_EVENT)

        # --- 等待程序結束並獲取輸出 ---
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            pytest.fail(f"程序在發送關機信號後未能終止。\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

        # --- 開始斷言 ---
        # 1. 驗證標準錯誤輸出
        assert "Traceback" not in stderr, f"STDERR 中出現了非預期的 Traceback:\n{stderr}"
        assert "Error" not in stderr, f"STDERR 中出現了非預期的 Error:\n{stderr}"

        # 2. 驗證標準輸出
        assert "CPU:" in stdout, "STDOUT 中未找到 'CPU:' 關鍵字。"
        assert "RAM:" in stdout, "STDOUT 中未找到 'RAM:' 關鍵字。"
        assert "快速運行模式" in stdout, "STDOUT 中未找到 '快速運行模式'，表示 --fast-run 未生效。"
        assert "使用者請求關機..." in stdout, "STDOUT 中未找到優雅關機的訊息。"
        assert "鳳凰之心系統已安全關閉" in stdout, "STDOUT 中未找到最終的關閉訊息。"

        # 3. 驗證產生的檔案
        assert os.path.exists(LOG_DB), "logs.sqlite 資料庫檔案未被建立。"
        assert os.path.exists(LOG_ARCHIVE_DIR), "作戰日誌歸檔目錄未被建立。"

        archive_files = os.listdir(LOG_ARCHIVE_DIR)
        assert len(archive_files) > 0, "日誌歸檔目錄是空的。"

        # 讀取歸檔內容並驗證
        archive_content = ""
        with open(os.path.join(LOG_ARCHIVE_DIR, archive_files[0]), 'r', encoding='utf-8') as f:
            archive_content = f.read()

        assert "執行摘要" in archive_content, "歸檔日誌中未找到「執行摘要」。"
        assert "總體結果: ✅ 成功" in archive_content, "歸檔日誌的最終狀態不正確。"

    finally:
        # 確保無論測試成功或失敗，子程序都會被終止
        if process.poll() is None:
            process.kill()
            process.communicate()
