#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系統監控獨立工具 (System Monitoring Tool)

功能:
1.  自我管理虛擬環境和依賴 (`pydantic`, `psutil`)。
2.  執行前進行系統資源檢查。
3.  使用看門狗（Watchdog）計時器，防止腳本意外卡死。
4.  獲取當前的 CPU 和記憶體使用率。
5.  將結果以 JSON 格式輸出到標準輸出 (stdout)。
6.  將日誌記錄輸出到標準錯誤 (stderr)。
"""
import os
import sys
import subprocess
import venv
import time
import json
import signal
from pathlib import Path

# --- 設定 ---
TOOL_NAME = "SystemMonitoringTool"
VENV_DIR = Path(__file__).parent / f".venv_{Path(__file__).stem}"
WATCHDOG_TIMEOUT = 15  # 秒，對於這個簡單的任務，15秒足夠了

# --- 依賴列表 ---
DEPENDENCIES = {
    "pydantic": "pydantic==2.11.7",
    "psutil": "psutil==7.0.0",
}

# --- 日誌記錄 ---
def log(message):
    """將日誌訊息寫入標準錯誤流。"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}][{TOOL_NAME}] {message}", file=sys.stderr)

# --- 看門狗 ---
class Watchdog:
    def __init__(self, seconds):
        self.seconds = seconds

    def __enter__(self):
        signal.signal(signal.SIGALRM, self._handle_timeout)
        signal.alarm(self.seconds)
        log(f"🛡️ 看門狗已啟動，超時設定為 {self.seconds} 秒。")

    def __exit__(self, exc_type, exc_value, traceback):
        signal.alarm(0) # 取消鬧鐘
        log("✅ 看門狗已解除。")

    def _handle_timeout(self, signum, frame):
        log(f"❌ 看門狗錯誤：腳本執行超過 {self.seconds} 秒，強制終止。")
        sys.exit(1)

# --- 核心功能 ---
def setup_environment():
    """設定虛擬環境並安裝依賴。"""
    if VENV_DIR.exists() and (VENV_DIR / ".tool_setup_complete").exists():
        return # 如果已經設定完成，直接返回

    log("🚀 開始環境設定...")
    if not VENV_DIR.exists():
        log(f"正在建立虛擬環境於: {VENV_DIR}")
        venv.create(VENV_DIR, with_pip=True)

    pip_executable = VENV_DIR / "bin" / "pip" if os.name != "nt" else VENV_DIR / "Scripts" / "pip.exe"

    log("📦 正在檢查並安裝依賴...")
    try:
        # 一次性安裝所有依賴，提高效率
        requirements = [spec for spec in DEPENDENCIES.values()]
        subprocess.check_call([str(pip_executable), "install", *requirements], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        log("✅ 所有依賴均已準備就緒。")
    except subprocess.CalledProcessError as e:
        log(f"❌ 依賴安裝失敗。錯誤: {e.stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)

    # 標記設定完成
    (VENV_DIR / ".tool_setup_complete").touch()


def activate_venv():
    """啟動虛擬環境，將其路徑加入到 sys.path。"""
    if not VENV_DIR.exists():
        log("❌ 虛擬環境目錄不存在，無法啟動。")
        sys.exit(1)

    site_packages = VENV_DIR / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if os.name == 'nt':
        site_packages = VENV_DIR / "Lib" / "site-packages"

    if not site_packages.exists():
        log(f"❌ 找不到 site-packages 目錄: {site_packages}")
        sys.exit(1)

    sys.path.insert(0, str(site_packages))


def get_system_usage():
    """
    獲取系統使用率並以 JSON 格式輸出。
    """
    import psutil
    from pydantic import BaseModel

    class SystemUsage(BaseModel):
        """定義系統使用率的數據模型。"""
        cpu_percent: float
        memory_percent: float

    log("💡 正在檢查系統資源...")
    mem = psutil.virtual_memory()
    if mem.percent > 90:
        log(f"⚠️ 警告：記憶體使用率偏高 ({mem.percent}%)。")

    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory_info = psutil.virtual_memory()

    usage_data = SystemUsage(
        cpu_percent=cpu_percent,
        memory_percent=memory_info.percent
    )

    log(f"📊 CPU: {cpu_percent}%, Memory: {memory_info.percent}%")

    # 將結果輸出到 stdout
    print(usage_data.model_dump_json())


def main():
    """主執行函數。"""
    log("--- 系統監控工具已啟動 ---")

    with Watchdog(WATCHDOG_TIMEOUT):
        setup_environment()
        activate_venv()
        get_system_usage()

    log("--- 系統監控工具執行完畢 ---")

if __name__ == "__main__":
    main()
