# 檔案: tests/integration/test_parameterization.py
# 說明: 驗證從設定檔到後端的參數化功能。 (修正版 2)
# 作者: Jules

import pytest
import subprocess
import sys
import json
import time
import httpx
import os
import shutil
from pathlib import Path

@pytest.fixture
def project_root() -> Path:
    """提供專案的根目錄路徑。"""
    return Path(__file__).resolve().parents[2]

def test_logging_level_parameterization(tmp_path, project_root):
    """
    測試後端服務是否能根據設定檔正確設定日誌等級。
    使用環境變數來重定向路徑，而不是修改原始碼。
    """
    # --- 準備 (Setup) ---
    # 1. 建立一個模擬的 config.json
    config_path = tmp_path / "test_config.json"
    config_data = {"log_level": "DEBUG"}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    # 2. 定義臨時路徑
    log_file_path = tmp_path / "test_run.log"
    db_file_path = tmp_path / "test_state.db"

    # 3. 將報告生成器腳本複製到臨時目錄，以便 launch.py 能找到它
    shutil.copy(project_root / "scripts" / "report_generator.py", tmp_path)

    # 4. 設定環境變數
    test_env = os.environ.copy()
    test_env["PHOENIX_DB_PATH"] = str(db_file_path)
    test_env["PHOENIX_LOG_PATH"] = str(log_file_path)

    # --- 執行 (Execution) ---
    # 5. 準備命令
    launch_script_path = project_root / "scripts" / "launch.py"
    command = [
        sys.executable,
        str(launch_script_path),
        "--config",
        str(config_path),
    ]

    # 6. 在背景啟動後端服務
    process = None
    try:
        process = subprocess.Popen(command, env=test_env, cwd=str(tmp_path))

        # 7. 等待服務啟動
        time.sleep(3)

        # --- 驗證 (Verification) ---
        # 8. 檢查日誌檔案是否存在
        assert log_file_path.exists(), f"日誌檔案未被建立於 {log_file_path}"

        # 9. 讀取日誌內容並斷言
        log_content = log_file_path.read_text(encoding="utf-8")
        debug_message = "這是一條 DEBUG 訊息，用來驗證日誌等級設定。"
        assert debug_message in log_content, "日誌檔案中未找到預期的 DEBUG 訊息"

    finally:
        # --- 清理 (Cleanup) ---
        # 10. 優雅地關閉後端服務
        if process:
            try:
                shutdown_url = "http://localhost:8088/api/v1/shutdown"
                with httpx.Client() as client:
                    # 增加重試邏輯以提高測試穩定性
                    for i in range(3):
                        try:
                            response = client.post(shutdown_url, timeout=3)
                            if response.status_code == 200:
                                print("成功發送關機信號。")
                                break
                        except httpx.ConnectError:
                            print(f"關機連接嘗試 {i+1} 失敗，稍後重試...")
                            time.sleep(1)
                    else:
                        pytest.fail("在多次嘗試後，無法連接到伺服器以關機。")

                process.wait(timeout=10)
            except Exception as e:
                print(f"關閉後端時發生錯誤: {e}")
                process.kill()
