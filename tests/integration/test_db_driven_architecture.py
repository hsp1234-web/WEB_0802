# 檔案: tests/integration/test_db_driven_architecture.py
# 說明: 驗證資料庫驅動架構的整合測試。

import subprocess
import sys
import time
import sqlite3
import multiprocessing
from pathlib import Path
import pytest
import os

# --- Fixtures ---

@pytest.fixture(scope="function")
def db_path():
    """提供一個臨時的資料庫路徑，並在測試後清理。"""
    path = Path("test_state.db")
    yield path
    if path.exists():
        os.remove(path)

@pytest.fixture(scope="function")
def log_path():
    """提供一個臨時的日誌檔案路徑，並在測試後清理。"""
    path = Path("test_uvicorn.log")
    yield path
    if path.exists():
        os.remove(path)

# --- 測試案例 ---

def test_launch_script_execution(db_path, log_path):
    """
    測試 launch.py 腳本是否能獨立、成功地執行，
    並在資料庫中留下正確的最終狀態。
    """
    # 為了測試，我們需要暫時將 DB_PATH 和 LOG_PATH 指向我們的測試檔案
    # 我們透過修改 launch.py 的內容來實現這一點
    with open("scripts/launch.py", "r", encoding="utf-8") as f:
        original_content = f.read()

    modified_content = original_content.replace(
        'DB_PATH = Path("state.db")', f'DB_PATH = Path("{db_path}")'
    ).replace(
        'LOG_PATH = Path("uvicorn.log")', f'LOG_PATH = Path("{log_path}")'
    )

    with open("scripts/launch.py", "w", encoding="utf-8") as f:
        f.write(modified_content)

    try:
        # 執行 launch.py
        result = subprocess.run(
            [sys.executable, "scripts/launch.py"],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )

        # 驗證資料庫狀態
        assert db_path.exists(), "資料庫檔案未被建立"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM status WHERE key = 'current_status'")
        final_status = cursor.fetchone()[0]
        conn.close()

        assert final_status == "任務成功完成", "資料庫中的最終狀態不正確"

        # 驗證報告是否生成 (假設報告生成器正常工作)
        # 這裡我們只檢查 launch.py 是否有嘗試呼叫它
        assert "準備生成最終報告..." in result.stdout
        assert "報告生成成功。" in result.stdout

    finally:
        # 無論如何都要恢復原始檔案
        with open("scripts/launch.py", "w", encoding="utf-8") as f:
            f.write(original_content)


def run_launch_script():
    """一個輔助函式，用於在背景進程中執行 launch.py。"""
    # 同樣，為了隔離，我們讓這個進程使用測試資料庫
    with open("scripts/launch.py", "r", encoding="utf-8") as f:
        original_content = f.read()
    modified_content = original_content.replace(
        'DB_PATH = Path("state.db")', 'DB_PATH = Path("test_state.db")'
    ).replace(
        'LOG_PATH = Path("uvicorn.log")', 'LOG_PATH = Path("test_uvicorn.log")'
    )
    with open("scripts/launch.py", "w", encoding="utf-8") as f:
        f.write(modified_content)

    try:
        subprocess.run([sys.executable, "scripts/launch.py"], check=True)
    finally:
        # 恢復
        with open("scripts/launch.py", "w", encoding="utf-8") as f:
            f.write(original_content)


def test_e2e_db_driven_flow(db_path, log_path):
    """
    測試端對端流程：背景執行 launch.py，主進程輪詢資料庫狀態。
    """
    # 在背景啟動 launch.py
    launch_process = multiprocessing.Process(target=run_launch_script)
    launch_process.start()

    # 主進程模擬 colab_runner.py 的行為
    detected_statuses = set()
    expected_statuses = {
        "後端服務已啟動",
        "核心任務：啟動中...",
        "核心任務：正在處理數據...",
        "核心任務：處理完畢。",
        "任務成功完成"
    }

    # 輪詢最多 20 秒
    for i in range(20):
        if not db_path.exists():
            time.sleep(1)
            continue

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM status WHERE key = 'current_status'")
            result = cursor.fetchone()
            conn.close()
            if result:
                detected_statuses.add(result[0])
                # 如果我們已經看到了所有預期狀態，可以提前結束
                if detected_statuses.issuperset(expected_statuses):
                    break
        except sqlite3.OperationalError:
            # 資料庫可能正在被寫入，稍後重試
            pass

        time.sleep(1)

    # 確保 launch.py 進程已結束
    launch_process.join(timeout=5)
    if launch_process.is_alive():
        launch_process.kill()
        pytest.fail("launch.py 進程在測試結束後仍在運行")

    # 斷言我們是否觀察到了所有預期的狀態
    assert detected_statuses.issuperset(expected_statuses), \
        f"未能觀察到所有預期的狀態。預期: {expected_statuses}, 實際觀察到: {detected_statuses}"
