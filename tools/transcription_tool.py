# -*- coding: utf-8 -*-
"""
語音轉錄獨立工具 (Transcription Tool)

功能:
1.  自我管理虛擬環境和依賴。
2.  執行前進行系統資源檢查。
3.  使用看門狗監控轉錄過程，防止卡死。
4.  從指定目錄讀取音訊檔，使用 faster-whisper 進行轉錄。
5.  使用 'tiny' 模型和 'int8' 精度以實現高效能。
6.  使用 SHA256 雜湊值避免重複處理已轉錄的檔案。
"""
import os
import sys
import subprocess
import venv
import time
import hashlib
import threading
from pathlib import Path

# --- 設定 ---
TOOL_NAME = "TranscriptionTool"
VENV_DIR = Path(__file__).parent / ".venv_transcription"
AUDIO_DIR = Path("./storage/transcription_uploads")
PROCESSED_HASHES_DIR = Path("./storage/processed_hashes")
WATCHDOG_TIMEOUT = 15  # 秒
LOG_FILE = Path(__file__).parent / "transcription_tool.log"

# --- 依賴列表 ---
DEPENDENCIES = {
    "torch": "torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu",
    "faster-whisper": "faster-whisper==1.2.0",
    "ctranslate2": "ctranslate2==4.6.0",
    "psutil": "psutil",
}

# --- 日誌記錄 ---
def log(message):
    """將日誌訊息寫入檔案和控制台。"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}][{TOOL_NAME}] {message}"
    print(log_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")

# --- 核心功能 ---

def check_resources():
    """檢查系統資源是否充足。"""
    import psutil
    import shutil
    log("正在檢查系統資源...")
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    MEM_THRESHOLD = 75  # %
    DISK_FREE_THRESHOLD_GB = 1  # GB

    mem_ok = mem.percent < MEM_THRESHOLD
    disk_free_gb = disk.free / (1024**3)
    disk_ok = disk_free_gb > DISK_FREE_THRESHOLD_GB

    if not mem_ok or not disk_ok:
        log(f"錯誤：資源不足！記憶體使用率: {mem.percent}% (閾值: {MEM_THRESHOLD}%), "
            f"可用磁碟空間: {disk_free_gb:.2f}GB (閾值: {DISK_FREE_THRESHOLD_GB}GB)")
        sys.exit(1)
    log("系統資源充足。")
    return True

def setup_environment():
    """設定虛擬環境並安裝依賴。"""
    log("正在設定虛擬環境...")
    if not VENV_DIR.exists():
        log(f"正在建立虛擬環境於: {VENV_DIR}")
        venv.create(VENV_DIR, with_pip=True)

    pip_executable = VENV_DIR / "bin" / "pip" if os.name != "nt" else VENV_DIR / "Scripts" / "pip.exe"

    for lib, install_spec in DEPENDENCIES.items():
        try:
            # 檢查套件是否已安裝
            subprocess.check_call([str(pip_executable), "show", lib.split('==')[0]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log(f"依賴 '{lib}' 已安裝。")
        except subprocess.CalledProcessError:
            log(f"正在安裝依賴: {lib}...")
            # 使用 shell=True 來正確處理複雜的命令，例如帶有 --index-url
            subprocess.check_call(f'"{pip_executable}" install {install_spec}', shell=True)
            log(f"依賴 '{lib}' 安裝成功。")

def get_file_sha256(filepath: Path) -> str:
    """計算檔案的 SHA256 雜湊值。"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def run_transcription_subprocess():
    """
    這是在子程序中運行的實際轉錄邏輯。
    這樣做是為了讓主程序可以作為看門狗監控它。
    """
    # 子程序的第一步是檢查資源，因為它在正確的 venv 中運行
    check_resources()

    from faster_whisper import WhisperModel

    log("子程序：開始轉錄任務。")
    model_size = "tiny"
    compute_type = "int8"

    try:
        model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
        log(f"子程序：成功載入模型 '{model_size}' (精度: {compute_type})。")
    except Exception as e:
        log(f"子程序錯誤：模型載入失敗 - {e}")
        return # 退出子程序

    if not AUDIO_DIR.exists() or not any(AUDIO_DIR.iterdir()):
        log("子程序：找不到音訊檔案或目錄不存在，無需處理。")
        return

    PROCESSED_HASHES_DIR.mkdir(exist_ok=True)

    for audio_file in AUDIO_DIR.iterdir():
        if audio_file.is_file() and audio_file.suffix.lower() in ['.wav', '.mp3', '.m4a']:
            log(f"子程序：正在處理檔案: {audio_file.name}")
            try:
                file_hash = get_file_sha256(audio_file)
                hash_file = PROCESSED_HASHES_DIR / file_hash

                if hash_file.exists():
                    log(f"子程序：檔案 '{audio_file.name}' (雜湊: {file_hash[:8]}...) 已處理過，跳過。")
                    continue

                segments, info = model.transcribe(str(audio_file), beam_size=5)
                log(f"子程序：偵測到語言 '{info.language}'，概率 {info.language_probability:.2f}")

                transcription_text = "".join([segment.text for segment in segments])

                # 簡單地將結果寫入日誌
                log(f"--- 轉錄結果 START ---")
                log(f"檔案: {audio_file.name}")
                log(f"內容: {transcription_text}")
                log(f"--- 轉錄結果 END ---")

                # 標記為已處理
                hash_file.touch()
                log(f"子程序：已為 '{audio_file.name}' 建立處理標記。")

            except Exception as e:
                log(f"子程序錯誤：處理檔案 '{audio_file.name}' 時發生錯誤: {e}")
    log("子程序：所有檔案處理完畢。")


def main():
    """主函數，負責啟動、監控。"""
    log("--- 語音轉錄工具已啟動 ---")

    # 1. 環境設定
    # 這必須是第一步，以確保所有依賴都已安裝。
    setup_environment()

    # 2. 啟動看門狗和子程序
    #    資源檢查現在由子程序自己在內部完成。
    log("準備啟動帶有看門狗的轉錄子程序...")
    python_executable = VENV_DIR / "bin" / "python" if os.name != "nt" else VENV_DIR / "Scripts" / "python.exe"

    # 我們需要一種方式來從這個腳本內部調用子程序邏輯
    # 我們可以通過傳遞一個參數來做到這一點
    command = [str(python_executable), __file__, "--run-child"]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        bufsize=1
    )

    last_output_time = time.time()

    def watchdog():
        while process.poll() is None:
            if time.time() - last_output_time > WATCHDOG_TIMEOUT:
                log(f"看門狗錯誤：子程序在 {WATCHDOG_TIMEOUT} 秒內無任何輸出，強制終止！")
                process.kill()
                break
            time.sleep(1)

    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
    watchdog_thread.start()

    # 讀取子程序的輸出
    for line in iter(process.stdout.readline, ''):
        log(f"[子程序輸出] {line.strip()}")
        last_output_time = time.time()

    process.wait()
    log(f"子程序已結束，返回碼: {process.returncode}")

    if process.returncode != 0:
        log("錯誤：轉錄子程序執行失敗。")
        sys.exit(1)

    log("--- 語音轉錄工具執行完畢 ---")


if __name__ == "__main__":
    # 檢查是否作為子程序運行
    if "--run-child" in sys.argv:
        run_transcription_subprocess()
    else:
        main()
