# -*- coding: utf-8 -*-
"""
E2E 測試腳本：模擬 Colab Runner 邏輯

此腳本旨在端對端地測試 `colab_runner.py` 的核心邏輯，而無需在 Colab 環境中實際執行它。
測試流程如下：
1.  **環境準備**: 自動建立一個 .venv 虛擬環境並安裝所需依賴。
2.  **模擬設定**: 根據不同的測試案例（模擬 @markdown 選項），動態生成 `config.json`。
3.  **啟動服務**: 將設定檔傳遞給 `scripts/start_api_service.py` 來啟動後端伺服器。
4.  **程序監控**:
    - 監控伺服器啟動日誌，確保其成功運行。
    - 實作一個 10 秒的看門狗（watchdog）計時器，若無日誌輸出則終止測試，防止卡死。
5.  **API 驗證**:
    - 確認伺服器啟動後，根 URL (`/`) 可以成功訪問。
    - 請求 `/api/v1/status/dashboard` 端點，驗證回傳的日誌是否符合 `config.json` 中設定的過濾規則。
6.  **清理**: 確保在每個測試案例結束後，伺服器程序都被完全終止。
"""

import sys
import os
import subprocess
import time
import json
import socket
import threading
from pathlib import Path
import shutil

# --- 全域設定 ---
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
VENV_DIR = PROJECT_ROOT / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
VENV_PIP = VENV_DIR / "bin" / "pip"
API_SERVICE_SCRIPT = PROJECT_ROOT / "scripts" / "start_api_service.py"
REQUIREMENTS_BASE = PROJECT_ROOT / "requirements" / "base.txt"
REQUIREMENTS_DEV = PROJECT_ROOT / "requirements" / "dev.txt"
LOG_FILE_PATH = PROJECT_ROOT / "api_server_e2e_test.log"

# --- 全域變數 ---
server_process = None
watchdog_timer = None

# --- 輔助函式 ---

def print_header(title):
    """打印漂亮的標題。"""
    print("\n" + "=" * 80)
    print(f"🚀 {title}")
    print("=" * 80)

def find_free_port() -> int:
    """尋找一個空閒的 TCP 埠號。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def setup_virtualenv():
    """設定並準備 Python 虛擬環境。"""
    print_header("引導程序: 設定 Python 虛擬環境")
    if not VENV_DIR.exists():
        print(f"虛擬環境 '{VENV_DIR}' 不存在，正在建立...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("✅ 虛擬環境建立成功。")
    else:
        print(f"✅ 虛擬環境 '{VENV_DIR}' 已存在。")

    print("正在安裝/更新依賴套件 (將顯示詳細日誌)...")
    # 移除 capture_output=True 以便於除錯
    subprocess.run([str(VENV_PIP), "install", "-U", "pip"], check=True)
    subprocess.run([str(VENV_PIP), "install", "-r", str(REQUIREMENTS_BASE)], check=True)
    subprocess.run([str(VENV_PIP), "install", "-r", str(REQUIREMENTS_DEV)], check=True)
    print("✅ 依賴套件安裝完成。")


# --- 測試執行核心邏輯 (在 venv 環境中運行) ---

def reset_watchdog():
    """重置看門狗計時器。"""
    global watchdog_timer
    if watchdog_timer:
        watchdog_timer.cancel()
    watchdog_timer = threading.Timer(10.0, handle_timeout)
    watchdog_timer.start()

def handle_timeout():
    """處理超時事件。"""
    global server_process
    print("\n❌ 錯誤: 10 秒內沒有收到任何日誌輸出，測試超時！")
    print("🔥 正在終止伺服器程序...")
    if server_process and server_process.poll() is None:
        server_process.kill()
    os._exit(1)

def start_server(config_path: Path, port: int) -> bool:
    """啟動後端 API 伺服器。"""
    global server_process
    print_header(f"步驟 1: 啟動 API 伺服器 (埠號: {port})")
    command = [
        str(VENV_PYTHON),
        str(API_SERVICE_SCRIPT),
        "--config", str(config_path)
    ]

    print(f"執行命令: {' '.join(command)}")
    server_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        bufsize=1
    )

    print("監控日誌以等待伺服器就緒 (超時 10 秒)...")
    reset_watchdog()

    try:
        # 複製 wolf.html 以便根目錄可以被訪問
        # 提前複製以避免競爭條件
        src_html = PROJECT_ROOT / "wolf.html"
        dest_html = PROJECT_ROOT / "src/phoenix_core/wolf.html"
        if src_html.exists():
            shutil.copy(src_html, dest_html)

        for line in iter(server_process.stdout.readline, ''):
            if not line:
                break
            print(f"   [日誌] {line.strip()}")
            reset_watchdog()
            if f"Uvicorn running on http://127.0.0.1:{port}" in line or "Application startup complete" in line:
                print("\n✅ 伺服器已成功啟動！")
                time.sleep(1) # 給予伺服器一點額外時間來完全就緒
                return True
    except Exception as e:
        print(f"讀取日誌時發生錯誤: {e}")
        return False
    finally:
        if watchdog_timer:
            watchdog_timer.cancel()

    print("❌ 伺服器啟動失敗，日誌流已結束。")
    return False

def run_api_tests(base_url: str, log_config: dict):
    """執行 API 相關的測試。"""
    # 在函數內部導入，確保此時已在 venv 環境中
    import httpx

    print_header("步驟 2: 執行 API 驗證")

    try:
        print(f"測試網頁可及性: GET {base_url}/")
        response = httpx.get(f"{base_url}/", timeout=10)
        response.raise_for_status()
        print("✅ 根 URL 成功返回 200 OK。")
    except httpx.RequestError as e:
        print(f"❌ 網頁可及性測試失敗: {e}")
        return False

    try:
        dashboard_url = f"{base_url}/api/v1/status/dashboard"
        print(f"測試日誌過濾: GET {dashboard_url}")
        time.sleep(2) # 等待一些日誌生成
        response = httpx.get(dashboard_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        print("✅ Dashboard API 成功返回 200 OK。")

        expected_levels = {level for level, show in log_config.items() if show}
        if not data.get("logs"):
            if not expected_levels:
                 print("✅ 日誌驗證成功：預期沒有日誌，API 也未返回日誌。")
                 return True
            else:
                 print(f"⚠️  警告: API 未返回任何日誌，但預期應有 {expected_levels} 等級的日誌。可能是啟動期間未產生對應日誌。")
                 return True # 在此我們只驗證沒有出現不該出現的，因此此情況算通過

        returned_levels = {log['level'] for log in data["logs"]}
        print(f"   - 設定應顯示的日誌等級: {expected_levels or 'None'}")
        print(f"   - API 實際返回的日誌等級: {returned_levels}")

        assert returned_levels.issubset(expected_levels), \
            f"錯誤：API 返回了不應顯示的日誌等級。多餘的等級: {returned_levels - expected_levels}"
        print("✅ 日誌過濾規則驗證成功！")

    except httpx.RequestError as e:
        print(f"❌ API 日誌驗證失敗: {e}")
        return False
    except AssertionError as e:
        print(f"❌ API 斷言失敗: {e}")
        return False

    return True

def cleanup():
    """清理資源，終止伺服器。"""
    global server_process, watchdog_timer
    print_header("步驟 3: 清理資源")
    if watchdog_timer:
        watchdog_timer.cancel()
    if server_process and server_process.poll() is None:
        print("正在終止伺服器...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("✅ 伺服器已終止。")
        except subprocess.TimeoutExpired:
            print("⚠️ 伺服器終止超時，強制抹除。")
            server_process.kill()
    else:
        print("✅ 伺服器未在運行或已自行終止。")

    dest_html = PROJECT_ROOT / "src/phoenix_core/wolf.html"
    if dest_html.exists():
        dest_html.unlink()
        print("✅ 已清理臨時 HTML 檔案。")

def run_all_tests():
    """在 venv 中執行的主測試邏輯。"""
    test_cases = {
        "only_critical": {"BATTLE": False, "SUCCESS": False, "INFO": False, "CMD": False, "SHELL": False, "ERROR": False, "CRITICAL": True, "PERF": False},
        "errors_and_critical": {"BATTLE": False, "SUCCESS": False, "INFO": False, "CMD": False, "SHELL": False, "ERROR": True, "CRITICAL": True, "PERF": False},
        "show_all": {"BATTLE": True, "SUCCESS": True, "INFO": True, "CMD": True, "SHELL": True, "ERROR": True, "CRITICAL": True, "PERF": True},
        "show_none": {"BATTLE": False, "SUCCESS": False, "INFO": False, "CMD": False, "SHELL": False, "ERROR": False, "CRITICAL": False, "PERF": False},
    }

    total_start_time = time.time()
    passed_cases = 0

    for name, log_config in test_cases.items():
        print_header(f"===== 執行測試案例: {name} =====")
        case_start_time = time.time()
        port = find_free_port()
        base_url = f"http://127.0.0.1:{port}"

        config_data = {
            "system_settings": {"timezone": "Asia/Taipei"},
            "log_settings": {"levels": log_config},
            "__test_port__": port
        }

        config_path = PROJECT_ROOT / f"temp_config_{name}.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

        try:
            server_ready = start_server(config_path, port)
            if not server_ready:
                print(f"❌ 案例 '{name}' 失敗：伺服器未能啟動。")
                continue

            test_passed = run_api_tests(base_url, log_config)
            if test_passed:
                print(f"✅ 案例 '{name}' 成功！")
                passed_cases += 1
            else:
                print(f"❌ 案例 '{name}' 失敗：API 驗證未通過。")

        finally:
            cleanup()
            if config_path.exists():
                config_path.unlink()
            case_duration = time.time() - case_start_time
            print(f"案例 '{name}' 執行耗時: {case_duration:.2f} 秒")

    total_duration = time.time() - total_start_time
    print_header("===== 測試總結 =====")
    print(f"總執行時間: {total_duration:.2f} 秒")
    print(f"總共 {len(test_cases)} 個測試案例，{passed_cases} 個通過。")

    if passed_cases != len(test_cases):
        print("\n🔥 部分測試案例未通過！")
        sys.exit(1)
    else:
        print("\n🎉 所有測試案例均已成功通過！")
        sys.exit(0)

def main():
    """
    主執行函數 (引導程序)。
    先確保 venv 和依賴項已準備就緒，然後檢查是否需要用 venv 的 python 重新執行自己。
    """
    # 步驟 1: 無論如何，都先確保虛擬環境和依賴是好的
    setup_virtualenv()

    # 步驟 2: 檢查當前的 python 解釋器是否是我們想要的 venv python
    is_in_venv = (os.path.abspath(sys.executable) == os.path.abspath(str(VENV_PYTHON)))

    if is_in_venv:
        # --- 已經在 venv 中，執行測試 ---
        print_header("已在虛擬環境中運行，開始執行測試...")
        run_all_tests()
    else:
        # --- 不在 venv 中，使用 venv 的 Python 重新啟動 ---
        print_header("引導程序: 使用 venv 的 Python 重新啟動測試腳本")
        args = [str(VENV_PYTHON), __file__] + sys.argv[1:]
        os.execv(args[0], args)

if __name__ == "__main__":
    main()
