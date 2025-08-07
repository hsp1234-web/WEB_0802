# -*- coding: utf-8 -*-
"""
對 `tools/transcription_tool.py` 的整合測試。
"""
import os
import subprocess
import sys
import pytest
from pathlib import Path
import shutil

# --- 設定 ---
TOOL_SCRIPT = Path(__file__).parent.parent.parent / "tools" / "transcription_tool.py"
AUDIO_DIR = Path(__file__).parent.parent.parent / "storage" / "transcription_uploads"
PROCESSED_HASHES_DIR = Path(__file__).parent.parent.parent / "storage" / "processed_hashes"
LOG_FILE = Path(__file__).parent.parent.parent / "tools" / "transcription_tool.log"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """在每次測試前後執行，確保環境乾淨且目錄存在。"""
    # 清理日誌
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    # 確保關鍵目錄存在且為空
    for dir_path in [PROCESSED_HASHES_DIR, AUDIO_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
        dir_path.mkdir(parents=True)

    yield  # 執行測試


def run_tool():
    """執行工具並回傳結果。"""
    command = [sys.executable, str(TOOL_SCRIPT)]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    return result

def create_dummy_wav(filepath: Path, duration_ms: int = 100):
    """建立一個有效的、靜音的 WAV 檔案。"""
    import wave
    import struct

    sample_rate = 16000
    num_channels = 1
    samp_width = 2
    num_frames = int(sample_rate * (duration_ms / 1000.0))

    with wave.open(str(filepath), 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(samp_width)
        wf.setframerate(sample_rate)

        # 寫入靜音幀
        for _ in range(num_frames):
            wf.writeframes(struct.pack('<h', 0))

def test_transcription_with_audio_files():
    """
    測試案例 1：當存在音訊檔時，工具能否正常執行並處理檔案。
    """
    # 準備：建立一個假的音訊檔
    dummy_file = AUDIO_DIR / "test.wav"
    create_dummy_wav(dummy_file)
    assert dummy_file.exists()

    # 執行工具
    result = run_tool()

    # 驗證
    assert result.returncode == 0, f"工具執行失敗，返回碼非零。\n輸出:\n{result.stdout}\n錯誤:\n{result.stderr}"

    log_content = LOG_FILE.read_text(encoding='utf-8')
    assert "--- 語音轉錄工具執行完畢 ---" in log_content
    assert "子程序：成功載入模型" in log_content
    assert "子程序：已為" in log_content # 檢查是否有名為 "已為...建立處理標記" 的日誌

    # 檢查是否有雜湊檔案被建立
    assert any(PROCESSED_HASHES_DIR.iterdir()), "處理後，雜湊目錄不應為空"

def test_transcription_without_audio_files():
    """
    測試案例 2：當不存在音訊檔時，工具應優雅退出。
    """
    # 準備：移動所有音訊檔
    temp_dir = AUDIO_DIR.parent / "temp_audio_backup"
    if AUDIO_DIR.exists():
        shutil.move(str(AUDIO_DIR), str(temp_dir))

    # 執行工具
    result = run_tool()

    # 驗證
    assert result.returncode == 0, f"工具在沒有音訊檔時執行失敗。\n輸出:\n{result.stdout}\n錯誤:\n{result.stderr}"
    log_content = LOG_FILE.read_text(encoding='utf-8')
    assert "子程序：找不到音訊檔案或目錄不存在，無需處理" in log_content

    # 清理：移回音訊檔
    if temp_dir.exists():
        shutil.move(str(temp_dir), str(AUDIO_DIR))

def test_skipping_processed_files():
    """
    測試案例 3：工具應能跳過已經處理過的檔案。
    """
    # 準備：建立一個假的音訊檔
    dummy_file = AUDIO_DIR / "test_for_skip.wav"
    create_dummy_wav(dummy_file)

    # 第一次執行
    res1 = run_tool()
    assert res1.returncode == 0
    log_content_1 = LOG_FILE.read_text(encoding='utf-8')
    assert "子程序：已為" in log_content_1 # 確保有檔案被處理

    # 第二次執行
    # 清除舊日誌以便檢查
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    res2 = run_tool()
    assert res2.returncode == 0
    log_content_2 = LOG_FILE.read_text(encoding='utf-8')

    # 驗證第二次執行時，所有檔案都被跳過
    assert "已處理過，跳過" in log_content_2
    assert "子程序：已為" not in log_content_2 # 不應再有新的處理標記建立
