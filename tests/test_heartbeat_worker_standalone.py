# -*- coding: utf-8 -*-
# 檔案: tests/test_heartbeat_worker_standalone.py
# 說明: 一個獨立的單元測試，用於在 pytest 環境中直接執行 heartbeat_worker，
#       以捕捉在 supervisor 中可能被隱藏的錯誤。

import sys
from pathlib import Path
import pytest
import subprocess
import time

def test_heartbeat_worker_execution():
    """
    測試 heartbeat_worker.py 是否可以作為一個獨立的子行程成功運行一小段時間。
    """
    project_root = Path(__file__).resolve().parents[1]
    heartbeat_script_path = project_root / "scripts" / "heartbeat_worker.py"

    assert heartbeat_script_path.exists(), "心跳工作者腳本不存在"

    # 使用 subprocess.run 啟動腳本，並設置一個短暫的超時
    # 這會模擬 supervisor 的行為，但在一個更受控的測試環境中
    try:
        result = subprocess.run(
            [sys.executable, str(heartbeat_script_path)],
            capture_output=True,
            text=True,
            timeout=10,  # 10 秒超時
            encoding='utf-8',
            cwd=project_root # 確保工作目錄正確
        )

        # 檢查腳本的輸出
        # 我們預期它會印出啟動訊息和至少一次心跳更新
        assert "心跳工作者啟動" in result.stdout, "腳本沒有印出預期的啟動訊息"
        assert "Heartbeat updated" in result.stdout, "腳本沒有印出預期的心跳更新訊息"

        # 腳本的正常行為是無限迴圈，所以它應該是因為超時而被終止
        # 但在這裡，我們檢查它在被終止前是否回報了任何錯誤
        assert result.returncode != 0, "腳本意外地正常結束了"

    except subprocess.TimeoutExpired as e:
        # 這是預期的結果，因為腳本是無限迴圈
        # 我們檢查在超時前，它是否有輸出
        stdout = e.stdout or ""
        stderr = e.stderr or ""

        print("\n--- Heartbeat Worker STDOUT (Timeout) ---")
        print(stdout)
        print("--- Heartbeat Worker STDERR (Timeout) ---")
        print(stderr)
        print("-----------------------------------------")

        assert "心跳工作者啟動" in stdout, "腳本在超時前沒有印出預期的啟動訊息"
        assert "Heartbeat updated" in stdout, "腳本在超時前沒有印出預期的心跳更新訊息"
        assert not stderr, "腳本在超時前不應有錯誤輸出"

    except Exception as e:
        pytest.fail(f"執行心跳工作者時發生未預期的例外: {e}")
