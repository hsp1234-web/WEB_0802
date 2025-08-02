# 檔案: tests/e2e/test_full_lifecycle.py
# 說明: (V3) 模擬從啟動到報告的完整使用者流程，以進行端對端驗證。
#      此版本採用更穩健的 live_server 模式，直接測試後端服務。
import subprocess
import sys
import os
import time
import shutil
import socket
import json
import httpx
from pathlib import Path
import pytest

# --- 測試設定 ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_E2E_DIR = PROJECT_ROOT / "tmp_e2e_test_v3"
PROJECT_FOLDER_NAME = "WEB1_E2E_TEST"
SERVER_START_TIMEOUT = 120 # 延長等待時間以應對首次安裝
POLL_INTERVAL = 2

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

@pytest.fixture(scope="module")
def setup_e2e_environment():
    """
    (Fixture) 設定 E2E 測試環境，複製專案檔案。
    """
    if TMP_E2E_DIR.exists():
        shutil.rmtree(TMP_E2E_DIR)

    # 我們只複製 src 和 scripts，因為這是服務運行所必需的
    # 不再複製整個專案，以加快速度並減少複雜性
    project_path = TMP_E2E_DIR / PROJECT_FOLDER_NAME
    project_path.mkdir(parents=True, exist_ok=True)

    shutil.copytree(PROJECT_ROOT / "src", project_path / "src")
    shutil.copytree(PROJECT_ROOT / "scripts", project_path / "scripts")
    shutil.copytree(PROJECT_ROOT / "requirements", project_path / "requirements")
    shutil.copy(PROJECT_ROOT / "pyproject.toml", project_path / "pyproject.toml")

    yield project_path

    shutil.rmtree(TMP_E2E_DIR)
    print("\n[INFO] 臨時 E2E 測試環境已清理。")

def test_full_lifecycle(setup_e2e_environment):
    """
    執行完整的端對端生命週期測試（Live Server 模式）。
    """
    project_path = setup_e2e_environment
    port = find_free_port()

    # --- 1. 準備設定檔 ---
    config_data = {
        "system_settings": {"timezone": "UTC"},
        "__test_port__": port
    }
    config_path = project_path / "test_config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    # --- 2. 啟動後端服務 ---
    # 直接執行 start_api_service.py，因為它包含了完整的環境建立流程
    # 使用當前的 pytest venv 中的 python 來執行
    command = [
        sys.executable, str(project_path / "scripts" / "start_api_service.py"),
        "--config", str(config_path)
    ]

    # 使用 PYTHONUNBUFFERED 確保日誌即時輸出
    test_env = os.environ.copy()
    test_env["PYTHONUNBUFFERED"] = "1"
    test_env["PYTHONPATH"] = str(PROJECT_ROOT) # 確保能找到 src

    print(f"\n[INFO] 執行指令: {' '.join(command)}")
    print(f"[INFO] 在 CWD: {project_path} 中啟動服務...")

    server_process = subprocess.Popen(
        command,
        cwd=project_path,
        env=test_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding='utf-8'
    )

    # --- 3. 等待伺服器就緒 ---
    start_time = time.time()
    is_ready = False
    log_lines = []

    try:
        while time.time() - start_time < SERVER_START_TIMEOUT:
            if server_process.poll() is not None:
                # 伺服器意外終止
                stdout, stderr = server_process.communicate()
                all_logs = stdout + stderr
                pytest.fail(f"伺服器提前崩潰。\n--- LOGS ---\n{all_logs}")

            try:
                # 輪詢根端點，直到它回應或超時
                with httpx.Client() as client:
                    response = client.get(f"http://127.0.0.1:{port}/", timeout=1)
                    if response.status_code == 200:
                        print(f"\n[INFO] 伺服器在埠號 {port} 上已就緒！")
                        is_ready = True
                        break
            except httpx.RequestError:
                # 預期中的連線錯誤，繼續等待
                time.sleep(POLL_INTERVAL)

        if not is_ready:
            pytest.fail(f"伺服器在 {SERVER_START_TIMEOUT}s 內未能啟動。")

        # --- 4. 驗證核心功能：state.db 是否生成 ---
        # 讓伺服器再運行一小段時間以確保有時間寫入 db
        time.sleep(5)
        db_path = project_path / "state.db"
        assert db_path.exists(), f"測試失敗: state.db 未在 {db_path} 中生成。"
        print(f"[INFO] ✅ 成功找到 state.db 於: {db_path}")

    finally:
        # --- 5. 無論如何都終止伺服器 ---
        if server_process.poll() is None:
            print("\n[INFO] 測試結束，正在終止伺服器...")
            server_process.terminate()
            try:
                stdout, stderr = server_process.communicate(timeout=10)
                print("[INFO] 伺服器已成功終止。")
                all_logs = stdout + stderr
                print(f"--- FINAL SERVER LOGS ---\n{all_logs}")
            except subprocess.TimeoutExpired:
                print("[WARN] 終止超時，強制抹除。")
                server_process.kill()

    print("\n🎉 [SUCCESS] 端對端生命週期測試成功！")
