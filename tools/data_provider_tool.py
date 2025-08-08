# -*- coding: utf-8 -*-
"""
資料提供獨立工具 (Data Provider Tool) - v2 (烘烤模式)

功能:
1.  啟動時檢查並解壓縮預烘烤的虛擬環境。
2.  將依賴（pydantic, psutil）加入 sys.path。
3.  在單一進程中執行所有核心邏輯，不再使用子進程。
4.  獲取股票數據，優先讀取快取，若無則模擬 API 呼叫。
"""
import os
import sys
import time
import json
import tarfile
import shutil
from pathlib import Path
import datetime

# --- 設定 ---
TOOL_NAME = "DataProviderTool"
# 虛擬環境目錄名稱，與烘烤腳本中定義的保持一致
VENV_DIR = Path(__file__).parent / f".venv_{Path(__file__).stem}"
# 預烘烤環境存檔的路徑
BAKED_ENV_ARCHIVE = Path(__file__).parent.parent / "storage" / "baked_envs" / f"{VENV_DIR.name}.tar.gz"

CACHE_DIR = Path("./storage/cache/dataprovider")
LOG_FILE = Path(__file__).parent / "data_provider_tool.log"

# --- 依賴列表 (僅供參考，實際由烘烤腳本使用) ---
DEPENDENCIES = {
    "pydantic": "pydantic==2.11.7",
    "psutil": "psutil==7.0.0",
}

# --- 日誌記錄 ---
def log(message):
    """將日誌訊息寫入檔案和標準錯誤流。"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}][{TOOL_NAME}] {message}"
    print(log_message, file=sys.stderr)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    except IOError as e:
        print(f"[{timestamp}][{TOOL_NAME}] 警告: 無法寫入日誌檔案 {LOG_FILE}: {e}", file=sys.stderr)


# --- 環境準備 ---
def prepare_environment():
    """
    準備工具的執行環境。
    如果本地虛擬環境不存在，則從預烘烤的存檔中解壓縮。
    """
    if VENV_DIR.exists():
        log(f"✅ 虛擬環境 '{VENV_DIR.name}' 已存在。")
        return

    log(f"🔍 虛擬環境 '{VENV_DIR.name}' 不存在，正在尋找預烘烤的存檔...")
    if not BAKED_ENV_ARCHIVE.exists():
        log(f"❌ 嚴重錯誤：找不到預烘烤的環境存檔: {BAKED_ENV_ARCHIVE}")
        log("   請先執行 'python scripts/bake_tool_envs.py' 來建立環境存檔。")
        sys.exit(1)

    log(f"📦 找到存檔，正在解壓縮至 '{VENV_DIR.parent}'...")
    try:
        with tarfile.open(BAKED_ENV_ARCHIVE, "r:gz") as tar:
            tar.extractall(path=VENV_DIR.parent)
        log("✅ 環境解壓縮成功。")
    except Exception as e:
        log(f"❌ 解壓縮環境時發生錯誤: {e}")
        if VENV_DIR.exists():
            log(f"🧹 正在清理損壞的解壓縮目錄: {VENV_DIR}")
            shutil.rmtree(VENV_DIR)
        sys.exit(1)

def activate_venv():
    """啟動虛擬環境，將其 site-packages 路徑加入到 sys.path。"""
    site_packages = VENV_DIR / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if os.name == 'nt':
        site_packages = VENV_DIR / "Lib" / "site-packages"

    if not site_packages.exists():
        log(f"❌ 嚴重錯誤：在虛擬環境中找不到 site-packages 目錄: {site_packages}")
        sys.exit(1)

    log(f"🔌 正在將 '{site_packages}' 加入到 sys.path")
    sys.path.insert(0, str(site_packages))


# --- 核心功能 ---
def run_dataprovider_logic(symbol: str):
    """
    實際的資料獲取邏輯。
    """
    # 依賴現在可以安全地 import
    from pydantic import BaseModel
    import psutil

    log("💡 正在檢查系統資源...")
    mem = psutil.virtual_memory()
    if mem.percent > 90:
        log(f"⚠️ 警告：記憶體使用率較高 ({mem.percent}%)。")
    log("✅ 系統資源充足。")

    log(f"📈 開始為 '{symbol}' 獲取資料...")

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
        log(f"✅ 從快取命中讀取 '{symbol}' 的數據。")
        print(json.dumps(cached_data))
        return

    # 2. 快取未命中，模擬從外部 API 獲取
    log(f"💡 快取未命中。模擬向外部 API 查詢 '{symbol}' 的股價...")
    time.sleep(1) # 模擬網路延遲

    new_data = StockData(
        symbol=symbol,
        price=round(2330.0 + time.time() % 100, 2), # 價格加點隨機性
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    # 3. 將新數據寫入快取
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(new_data.model_dump(), f)
    log(f"✅ 已為 '{symbol}' 寫入新快取。")

    # 輸出結果
    print(json.dumps(new_data.model_dump()))
    log(f"🏁 '{symbol}' 資料獲取完畢。")


def main():
    """主函數，負責啟動、監控。"""
    log("--- 資料提供工具已啟動 (v2 烘烤模式) ---")

    if len(sys.argv) < 2:
        log("❌ 錯誤：請提供一個股票代碼作為參數。例如: python data_provider_tool.py TSM")
        sys.exit(1)
    symbol_to_fetch = sys.argv[1]

    # 1. 準備並啟動環境
    prepare_environment()
    activate_venv()

    # 2. 直接執行核心邏輯
    try:
        run_dataprovider_logic(symbol_to_fetch)
    except Exception as e:
        log(f"❌ 執行核心邏輯時發生未預期錯誤: {e}")
        sys.exit(1)

    log("--- 資料提供工具執行完畢 ---")

if __name__ == "__main__":
    main()
