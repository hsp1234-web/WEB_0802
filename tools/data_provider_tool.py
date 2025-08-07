# -*- coding: utf-8 -*-
"""
資料提供獨立工具 (Data Provider Tool)

功能:
1.  自我管理虛擬環境和依賴。
2.  執行前進行系統資源檢查。
3.  使用看門狗監控執行過程，防止卡死。
4.  獲取股票數據，優先讀取快取，若無則模擬 API 呼叫。
"""
import os
import sys
import subprocess
import venv
import time
import json
from pathlib import Path
import datetime

# --- 設定 ---
TOOL_NAME = "DataProviderTool"
VENV_DIR = Path(__file__).parent / ".venv_dataprovider"
CACHE_DIR = Path("./storage/cache/dataprovider")
WATCHDOG_TIMEOUT = 30  # 秒
LOG_FILE = Path(__file__).parent / "data_provider_tool.log"

# --- 依賴列表 ---
DEPENDENCIES = {
    "pydantic": "pydantic==2.11.7",
    "psutil": "psutil==7.0.0",
}

# --- 日誌記錄 ---
def log(message):
    """將日誌訊息寫入檔案和標準錯誤流。"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}][{TOOL_NAME}] {message}"
    print(log_message, file=sys.stderr)  # 輸出到 stderr
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")

# --- 核心功能 ---
def check_resources():
    """檢查系統資源是否充足。"""
    import psutil
    import shutil
    log("💡 正在檢查系統資源...")
    mem = psutil.virtual_memory()
    if mem.percent > 75:
        log(f"❌ 錯誤：記憶體使用率過高 ({mem.percent}%)，中止任務。")
        sys.exit(1)
    log("✅ 系統資源充足。")

def setup_environment():
    """設定虛擬環境並安裝依賴。"""
    log("🚀 開始環境設定...")
    if not VENV_DIR.exists():
        log(f"正在建立虛擬環境於: {VENV_DIR}")
        venv.create(VENV_DIR, with_pip=True)

    pip_executable = VENV_DIR / "bin" / "pip" if os.name != "nt" else VENV_DIR / "Scripts" / "pip.exe"

    for lib_name, install_spec in DEPENDENCIES.items():
        try:
            subprocess.check_call([str(pip_executable), "show", lib_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log(f"✅ 依賴 '{lib_name}' 已安裝。")
        except subprocess.CalledProcessError:
            log(f"📦 正在安裝依賴: {lib_name}...")
            start_time = time.time()
            try:
                subprocess.check_call(f'"{pip_executable}" install {install_spec}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                duration = time.time() - start_time
                log(f"✅ 依賴 '{lib_name}' 安裝成功 (耗時 {duration:.1f} 秒)。")
            except subprocess.CalledProcessError as e:
                log(f"❌ 依賴 '{lib_name}' 安裝失敗。錯誤: {e}")
                sys.exit(1)

def run_dataprovider_subprocess(symbol: str):
    """
    這是在子程序中運行的實際資料獲取邏輯。
    """
    from pydantic import BaseModel

    # --- 子程序內的邏輯 ---
    check_resources()
    log(f"📈 子程序：開始為 '{symbol}' 獲取資料...")

    class StockData(BaseModel):
        symbol: str
        price: float
        timestamp: str

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"stock_{symbol}.json"

    # 1. 嘗試從快取讀取
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        log(f"✅ 子程序：從快取命中讀取 '{symbol}' 的數據。")
        # 輸出結果到 stdout，以便主程序捕獲
        print(json.dumps(cached_data))
        return

    # 2. 快取未命中，模擬從外部 API 獲取
    log(f"💡 子程序：快取未命中。模擬向外部 API 查詢 '{symbol}' 的股價...")
    time.sleep(2) # 模擬網路延遲

    new_data = StockData(
        symbol=symbol,
        price=2330.0,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    # 3. 將新數據寫入快取
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(new_data.model_dump(), f)
    log(f"✅ 子程序：已為 '{symbol}' 寫入新快取。")

    # 輸出結果
    print(json.dumps(new_data.model_dump()))
    log(f"🏁 子程序：'{symbol}' 資料獲取完畢。")


def main():
    """主函數，負責啟動、監控。"""
    log("--- 資料提供工具已啟動 ---")

    # 接收股票代碼作為參數
    if len(sys.argv) < 2:
        log("❌ 錯誤：請提供一個股票代碼作為參數。例如: python data_provider_tool.py TSM")
        sys.exit(1)
    symbol_to_fetch = sys.argv[1]

    setup_environment()

    log(f"🛡️ 準備啟動子程序為 '{symbol_to_fetch}' 獲取資料...")
    python_executable = VENV_DIR / "bin" / "python" if os.name != "nt" else VENV_DIR / "Scripts" / "python.exe"

    command = [str(python_executable), __file__, "--run-child", symbol_to_fetch]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=WATCHDOG_TIMEOUT,
            check=True  # 如果返回碼非零，則引發 CalledProcessError
        )
        log("✅ 子程序成功執行。")
        # 將子程序的 stdout (JSON data) 直接打印到主程序的 stdout
        print(result.stdout.strip())

    except subprocess.TimeoutExpired:
        log(f"❌ 看門狗錯誤：子程序執行超過 {WATCHDOG_TIMEOUT} 秒，已終止。")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        log(f"❌ 子程序執行失敗，返回碼: {e.returncode}")
        log(f"子程序錯誤輸出:\n{e.stderr}")
        sys.exit(1)

    log("--- 資料提供工具執行完畢 ---")

if __name__ == "__main__":
    if "--run-child" in sys.argv:
        child_symbol = sys.argv[sys.argv.index("--run-child") + 1]
        run_dataprovider_subprocess(child_symbol)
    else:
        main()
