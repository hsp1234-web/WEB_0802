# -*- coding: utf-8 -*-
"""
整合測試：System Monitoring Tool

這個測試模組負責驗證 `tools/system_monitoring_tool.py` 的功能是否如預期般運作。
"""

import subprocess
import json
import sys
from pathlib import Path
import shutil

# --- 測試設定 ---
# 取得專案根目錄的絕對路徑
PROJECT_ROOT = Path(__file__).parent.parent.parent
# 組裝出要測試的工具的完整路徑
TOOL_PATH = PROJECT_ROOT / "tools" / "system_monitoring_tool.py"
# 組裝出該工具會建立的虛擬環境路徑
VENV_DIR = PROJECT_ROOT / "tools" / ".venv_system_monitoring_tool"

def run_tool():
    """
    執行 system_monitoring_tool.py 並返回其輸出。

    返回:
        tuple: (stdout, stderr, returncode)
    """
    # 確保工具存在
    if not TOOL_PATH.is_file():
        raise FileNotFoundError(f"測試目標工具不存在: {TOOL_PATH}")

    # 使用與執行 pytest 相同的 Python 解釋器來執行工具
    # 這樣可以確保一致性，並避免 PATH 的問題
    command = [sys.executable, str(TOOL_PATH)]

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        cwd=PROJECT_ROOT  # 在專案根目錄下執行，以確保相對路徑正確
    )
    return process.stdout, process.stderr, process.returncode

def setup_module(module):
    """
    在所有測試開始前執行的設定函數 (pytest hook)。
    用於清理任何可能由先前測試運行遺留的暫存檔。
    """
    if VENV_DIR.exists():
        print(f"\n--- 清理舊的虛擬環境: {VENV_DIR} ---")
        shutil.rmtree(VENV_DIR)

def teardown_module(module):
    """
    在所有測試結束後執行的清理函數 (pytest hook)。
    用於清理測試產生的暫存檔。
    """
    if VENV_DIR.exists():
        print(f"\n--- 清理測試產生的虛擬環境: {VENV_DIR} ---")
        shutil.rmtree(VENV_DIR)


# --- 測試案例 ---

def test_tool_runs_successfully():
    """
    測試：工具是否能成功執行並正常退出。
    """
    stdout, stderr, returncode = run_tool()

    # 1. 驗證返回碼
    # 工具應該要成功執行並返回 0
    assert returncode == 0, f"工具執行失敗！\n返回碼: {returncode}\nStderr:\n{stderr}"

    # 2. 驗證日誌輸出 (stderr)
    # Stderr 不應為空，且應包含啟動和結束的日誌訊息
    assert "系統監控工具已啟動" in stderr, "缺少啟動日誌"
    assert "所有依賴均已準備就緒" in stderr, "缺少依賴安裝成功的日誌"
    assert "看門狗已啟動" in stderr, "缺少看門狗啟動日誌"
    assert "系統監控工具執行完畢" in stderr, "缺少結束日誌"
    assert "看門狗已解除" in stderr, "缺少看門狗解除日誌"

def test_output_is_valid_json():
    """
    測試：工具的標準輸出 (stdout) 是否為有效的 JSON 格式。
    """
    stdout, _, returncode = run_tool()
    assert returncode == 0, "工具執行失敗，無法進行 JSON 驗證"

    # 嘗試解析 JSON
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        assert False, f"Stdout 輸出不是有效的 JSON 格式。\n收到的輸出:\n{stdout}"

    # 驗證 JSON 內容
    assert isinstance(data, dict), "JSON 頂層結構應為一個物件 (dict)"

def test_json_structure_and_values():
    """
    測試：JSON 輸出的結構和數值是否符合預期。
    """
    stdout, _, returncode = run_tool()
    assert returncode == 0, "工具執行失敗，無法進行數值驗證"

    data = json.loads(stdout)

    # 1. 驗證鍵的存在
    assert "cpu_percent" in data, "JSON 輸出中缺少 'cpu_percent' 鍵"
    assert "memory_percent" in data, "JSON 輸出中缺少 'memory_percent' 鍵"

    # 2. 驗證值的類型
    assert isinstance(data["cpu_percent"], float), "'cpu_percent' 的值應為浮點數"
    assert isinstance(data["memory_percent"], float), "'memory_percent' 的值應為浮點數"

    # 3. 驗證值的範圍
    # CPU 和記憶體使用率應該介於 0.0 和 100.0 之間
    assert 0.0 <= data["cpu_percent"] <= 100.0, f"CPU 使用率超出合理範圍: {data['cpu_percent']}"
    assert 0.0 <= data["memory_percent"] <= 100.0, f"記憶體使用率超出合理範圍: {data['memory_percent']}"
