import os
import sys
import time
import json
import threading
from pathlib import Path
import subprocess

# --- 組態設定 ---
TASK_BASE_DIR = Path("storage/tasks")
PENDING_DIR = TASK_BASE_DIR / "pending"
PROCESSING_DIR = TASK_BASE_DIR / "processing"
COMPLETED_DIR = TASK_BASE_DIR / "completed"
FAILED_DIR = TASK_BASE_DIR / "failed"
VENV_NAME = ".venv_transcription"
VENV_DIR = Path("tools") / VENV_NAME
# 在此處定義此工具所需的依賴
# 為保持範例簡單，我們暫時不加依賴
# 真實世界中可能是 ["faster-whisper", "ctranslate2"]
REQUIRED_PACKAGES = []

# --- 看門狗 (Watchdog) ---
watchdog_timer = None

def watchdog_timeout():
    """看門狗超時處理函式"""
    print(f"錯誤：看門狗超時！工具似乎已卡住超過 30 秒，強制退出。", file=sys.stderr)
    sys.exit(1)

def reset_watchdog(timeout=30.0):
    """重置看門狗計時器"""
    global watchdog_timer
    if watchdog_timer:
        watchdog_timer.cancel()
    watchdog_timer = threading.Timer(timeout, watchdog_timeout)
    watchdog_timer.start()

# --- 核心邏輯 ---
def process_task(task_path: Path):
    """處理單一任務檔案"""
    print(f"資訊：開始處理任務：{task_path.name}")

    try:
        with open(task_path, 'r+', encoding='utf-8') as f:
            task_data = json.load(f)

            # 模擬轉錄工作
            print(f"資訊：正在對檔案 '{task_data.get('file_path')}' 進行轉錄...")
            for i in range(5):
                reset_watchdog() # 在長時間操作中持續餵狗
                time.sleep(1)
                print(f"資訊：...進度 { (i+1) * 20 }%")

            result = "這是一段模擬的轉錄文本。"
            task_data['transcript'] = result
            task_data['status'] = 'completed'

            # 將結果寫回 JSON 檔案
            f.seek(0)
            json.dump(task_data, f, indent=4, ensure_ascii=False)
            f.truncate()

        print("資訊：轉錄成功。")
        return True

    except Exception as e:
        print(f"錯誤：處理任務 {task_path.name} 時發生錯誤: {e}", file=sys.stderr)
        # 可以選擇將錯誤訊息寫回 task_data
        return False

def main_logic():
    """工具的主邏輯，尋找並處理任務"""
    reset_watchdog()
    print("="*50)
    print("語音轉錄工具已啟動")
    print(f"正在監控信箱：{PENDING_DIR}")
    print("="*50)

    task_file = None
    try:
        # 1. 尋找任務
        task_files = sorted(list(PENDING_DIR.glob("*.json")))
        if not task_files:
            print("資訊：待處理信箱中沒有任務，工具將退出。")
            return

        task_file = task_files[0]
        processing_path = PROCESSING_DIR / task_file.name

        # 2. 原子性地移動任務以宣告所有權
        print(f"資訊：發現任務 {task_file.name}，正在鎖定...")
        os.rename(task_file, processing_path)
        print(f"資訊：成功鎖定任務，已移至 {processing_path}")
        reset_watchdog()

        # 3. 處理任務
        success = process_task(processing_path)

        # 4. 歸檔任務
        if success:
            final_path = COMPLETED_DIR / processing_path.name
            print(f"資訊：任務完成，正在歸檔至 {final_path}")
        else:
            final_path = FAILED_DIR / processing_path.name
            print(f"資訊：任務失敗，正在歸檔至 {final_path}")

        os.rename(processing_path, final_path)
        print(f"資訊：歸檔完成。")

    except FileNotFoundError:
        print("資訊：當我們嘗試鎖定任務時，它似乎已被另一個工具取走。")
    except Exception as e:
        print(f"錯誤：在主邏輯中發生未預期的錯誤: {e}", file=sys.stderr)
        # 如果在發生錯誤時我們正在處理一個檔案，將其移至失敗資料夾
        if task_file and os.path.exists(PROCESSING_DIR / task_file.name):
            os.rename(PROCESSING_DIR / task_file.name, FAILED_DIR / task_file.name)
            print(f"資訊：已將錯誤的任務 {task_file.name} 移至失敗資料夾。")
    finally:
        if watchdog_timer:
            watchdog_timer.cancel()
        print("="*50)
        print("語音轉錄工具已結束。")
        print("="*50)


# --- 自我引導 (Self-Bootstrapping) ---
def self_bootstrap():
    """
    檢查是否在正確的虛擬環境中，如果不是，則建立環境並重新啟動。
    """
    # 檢查標記，如果已在 venv 中，則直接返回 True
    if os.environ.get("IN_TRANSCRIPTION_VENV") == "1":
        return True

    # 檢查 venv 是否存在
    if not VENV_DIR.exists():
        print(f"資訊：虛擬環境 '{VENV_DIR}' 不存在，正在建立...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("資訊：虛擬環境建立成功。")

    # 檢查並安裝依賴
    if REQUIRED_PACKAGES:
        print("資訊：正在安裝依賴...")
        pip_path = VENV_DIR / ("Scripts" if os.name == "nt" else "bin") / "pip"
        subprocess.run([str(pip_path), "install"] + REQUIRED_PACKAGES, check=True)
        print("資訊：依賴安裝成功。")

    # 設定標記並重新啟動
    print("資訊：正在使用虛擬環境的 Python 重新啟動本腳本...")
    os.environ["IN_TRANSCRIPTION_VENV"] = "1"

    python_executable = VENV_DIR / ("Scripts" if os.name == "nt" else "bin") / "python"
    # 使用 execv 來用新程序替換當前程序
    os.execv(python_executable, [str(python_executable), __file__] + sys.argv[1:])

    # execv 之後的程式碼不會被執行
    return False


if __name__ == "__main__":
    # 由於 Colab/沙箱環境可能沒有 uv，我們在此使用內建的 venv
    # if self_bootstrap():
    #     main_logic()
    # 我們暫時註解掉自我引導，以便在當前環境中直接測試核心邏輯
    # 在真實部署中，應該取消註解上面的 if 區塊
    main_logic()
