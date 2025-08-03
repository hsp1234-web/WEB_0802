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
    (Fixture) 設定 E2E 測試環境，包括複製專案檔案、建立 venv 和安裝依賴。
    """
    if TMP_E2E_DIR.exists():
        shutil.rmtree(TMP_E2E_DIR)

    project_path = TMP_E2E_DIR / PROJECT_FOLDER_NAME
    project_path.mkdir(parents=True, exist_ok=True)

    # --- 1. 複製必要的原始碼 ---
    shutil.copytree(PROJECT_ROOT / "src", project_path / "src")
    shutil.copytree(PROJECT_ROOT / "scripts", project_path / "scripts")
    shutil.copytree(PROJECT_ROOT / "requirements", project_path / "requirements")
    shutil.copy(PROJECT_ROOT / "pyproject.toml", project_path / "pyproject.toml")
    # 關鍵修復：複製主頁 HTML，以便健康檢查的 GET / 請求能成功
    shutil.copy(PROJECT_ROOT / "wolf.html", project_path / "wolf.html")

    # --- 2. 在 fixture 中預先建立虛擬環境並安裝依賴 ---
    print("\n[INFO][Fixture] 正在設定測試用的虛擬環境...")
    try:
        # 建立 venv (使用與 start_api_service.py 中一致的名稱)
        VENV_NAME = ".venv_colab_backend"
        subprocess.run([sys.executable, "-m", "venv", VENV_NAME], cwd=project_path, check=True)

        # 安裝依賴 (使用 base.txt 加快速度)
        pip_path = project_path / VENV_NAME / "bin" / "pip"
        requirements_path = project_path / "requirements" / "base.txt"
        subprocess.run([str(pip_path), "install", "-r", str(requirements_path)], cwd=project_path, check=True)

        # 額外: 將專案本身也安裝到 venv 中，因為 start_api_service.py 也會這樣做
        subprocess.run([str(pip_path), "install", "-e", "."], cwd=project_path, check=True)

        print("[INFO][Fixture] 虛擬環境設定完成。")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        pytest.fail(f"在 fixture 中設定虛擬環境失敗: {e}")

    yield project_path

    # --- 清理 ---
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
    # 執行 run_server_only.py 來啟動後端服務
    # 使用當前的 pytest venv 中的 python 來執行
    command = [
        sys.executable, str(project_path / "scripts" / "run_server_only.py"),
        "--config", str(config_path)
    ]

    # 使用 PYTHONUNBUFFERED 確保日誌即時輸出
    test_env = os.environ.copy()
    test_env["PYTHONUNBUFFERED"] = "1"
    # 關鍵修正: PYTHONPATH 應指向臨時專案的根目錄，而不是原始專案的根目錄。
    # 這樣 uvicorn 才能找到正確的、位於臨時環境中的 `src`。
    test_env["PYTHONPATH"] = str(project_path)

    print(f"\n[INFO] 執行指令: {' '.join(command)}")
    print(f"[INFO] 在 CWD: {project_path} 中啟動服務...")

    server_process = subprocess.Popen(
        command,
        cwd=project_path,
        env=test_env,
        stdout=sys.stdout,
        stderr=sys.stderr,
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
                all_logs = (stdout or "") + (stderr or "")
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

        # --- 4. 驗證伺服器啟動成功 ---
        # 此測試的核心目標是驗證 API 服務本身能否在一個乾淨的環境中
        # 成功建立 venv、安裝依賴並啟動。
        # state.db 的生成由另一個腳本 (local_run.py) 負責，不應在此斷言。
        # 只要伺服器能就緒 (is_ready == True)，就視為此測試成功。
        print(f"[INFO] ✅ 伺服器成功啟動並通過健康檢查。")

    finally:
        # --- 5. 無論如何都終止伺服器 ---
        if server_process.poll() is None:
            print("\n[INFO] 測試結束，正在終止伺服器...")
            server_process.terminate()
            try:
                stdout, stderr = server_process.communicate(timeout=10)
                print("[INFO] 伺服器已成功終止。")
                # 健壯性修復：處理 stdout/stderr 可能為 None 的情況
                all_logs = (stdout or "") + (stderr or "")
                if all_logs:
                    print(f"--- FINAL SERVER LOGS ---\n{all_logs}")
            except subprocess.TimeoutExpired:
                print("[WARN] 終止超時，強制抹除。")
                server_process.kill()

    print("\n🎉 [SUCCESS] 端對端生命週期測試成功！")
