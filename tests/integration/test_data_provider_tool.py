# -*- coding: utf-8 -*-
"""
對 `tools/data_provider_tool.py` 的整合測試。
"""
import os
import subprocess
import sys
import pytest
from pathlib import Path
import shutil
import json

# --- 設定 ---
TOOL_SCRIPT = Path(__file__).parent.parent.parent / "tools" / "data_provider_tool.py"
CACHE_DIR = Path(__file__).parent.parent.parent / "storage" / "cache" / "dataprovider"
LOG_FILE = Path(__file__).parent.parent.parent / "tools" / "data_provider_tool.log"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """在每次測試前後執行，確保環境乾淨。"""
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True)
    yield

def run_tool(symbol: str = None):
    """執行工具並回傳結果。"""
    command = [sys.executable, str(TOOL_SCRIPT)]
    if symbol:
        command.append(symbol)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    return result

def test_cache_miss_and_creation():
    """
    測試案例 1：快取未命中時，應能模擬 API 呼叫並建立快取。
    """
    symbol = "GOOG"
    cache_file = CACHE_DIR / f"stock_{symbol}.json"
    assert not cache_file.exists()

    result = run_tool(symbol)

    assert result.returncode == 0
    assert cache_file.exists()

    log_content = LOG_FILE.read_text(encoding='utf-8')
    assert "快取未命中" in log_content

    # 驗證 stdout 的 JSON 輸出
    output_data = json.loads(result.stdout)
    assert output_data['symbol'] == symbol
    assert output_data['price'] == 2330.0

def test_cache_hit():
    """
    測試案例 2：快取命中時，應能直接從快取讀取。
    """
    symbol = "AAPL"

    # 第一次執行以建立快取
    res1 = run_tool(symbol)
    assert res1.returncode == 0

    # 第二次執行
    res2 = run_tool(symbol)
    assert res2.returncode == 0

    log_content = LOG_FILE.read_text(encoding='utf-8')
    assert "從快取命中讀取" in log_content

def test_missing_argument():
    """
    測試案例 3：未提供參數時，應失敗並提示錯誤。
    """
    result = run_tool() # 不帶參數

    assert result.returncode != 0
    log_content = LOG_FILE.read_text(encoding='utf-8')
    assert "錯誤：請提供一個股票代碼作為參數" in log_content
