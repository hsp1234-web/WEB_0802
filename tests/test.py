# -*- coding: utf-8 -*-
# 檔案: tests/test.py
# 說明: 這是專案唯一的測試檔案，整合了所有的單元、整合與部分端對端測試。

# ==============================================================================
# 1. IMPORTS - 從所有測試檔案中合併而來
# ==============================================================================
import pytest
import sqlite3
from datetime import datetime, timedelta, timezone
import subprocess
import sys
import os
import time
import json
import socket
import shutil
import httpx
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import signal

# ==============================================================================
# 2. SHARED FIXTURES - 來自原始的 conftest.py
# ==============================================================================
# 這些 fixtures 為所有測試案例提供共享的資源，例如模擬資料庫或檔案系統。

@pytest.fixture(scope="function")
def mock_db():
    """
    一個 pytest fixture，用於提供一個帶有模擬資料的記憶體 SQLite 資料庫。
    - scope="function": 確保每個測試函式都獲得一個乾淨、獨立的資料庫。
    """
    # 在記憶體中建立資料庫
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # --- 建立資料表 ---
    cursor.execute("""
    CREATE TABLE logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        level TEXT NOT NULL,
        source TEXT NOT NULL,
        message TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE status_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        key TEXT UNIQUE NOT NULL,
        value TEXT
    )
    """)

    # --- 插入模擬資料 ---
    now = datetime.now(timezone.utc)
    log_data = [
        (now, 'SUCCESS', 'DataProcessor', '資料處理成功，共 100 筆。'),
        (now, 'SUCCESS', 'DataProcessor', '資料處理成功，共 200 筆。'),
        (now, 'ERROR', 'APIConnector', 'API 連線失敗: timeout。'),
        (now, 'SUCCESS', 'DataProcessor', '資料處理成功，共 300 筆。'),
        (now, 'INFO', 'System', '系統啟動。'),
        (now, 'ERROR', 'Database', '資料庫寫入錯誤: disk full。'),
    ]
    cursor.executemany(
        "INSERT INTO logs (timestamp, level, source, message) VALUES (?, ?, ?, ?)",
        log_data
    )
    fresh_heartbeat_ts = now.isoformat()
    cursor.execute(
        "INSERT INTO status_updates (timestamp, key, value) VALUES (?, ?, ?)",
        (fresh_heartbeat_ts, 'system_heartbeat', 'OK')
    )
    conn.commit()
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def mock_report_files(tmp_path):
    """
    一個 pytest fixture，用於在臨時目錄中建立一組模擬的報告檔案。
    """
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "summary_report.md").write_text("這是總結報告。")
    (reports_dir / "detailed_log_report.md").write_text("這是詳細日誌報告。")
    (reports_dir / "performance_report.md").write_text("這是效能報告。")
    yield tmp_path

def find_free_port() -> int:
    """找到一個可用的埠號"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

@pytest.fixture(scope="module")
def live_server(request):
    """
    (Fixture) 啟動一個真實的後端 API 伺服器以供測試。
    """
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "master")
    tmp_test_dir = PROJECT_ROOT / f"tmp_pytest_test_{worker_id}"

    if tmp_test_dir.exists():
        shutil.rmtree(tmp_test_dir)
    tmp_test_dir.mkdir()

    python_executable = sys.executable
    port = find_free_port()
    config_path = tmp_test_dir / "config.json"
    db_path = tmp_test_dir / "state.db"
    test_env = os.environ.copy()
    test_env["PHOENIX_CONFIG_PATH"] = str(config_path)
    test_env["PHOENIX_DB_PATH"] = str(db_path)
    test_env["PYTHONPATH"] = str(PROJECT_ROOT)

    command = [
        str(python_executable), "-m", "uvicorn",
        "src.phoenix_core.main:app",
        "--host", "0.0.0.0",
        "--port", str(port)
    ]
    server_process = subprocess.Popen(command, env=test_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    is_ready = False
    for _ in range(20):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                is_ready = True
                break
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(0.5)

    if not is_ready:
        server_process.kill()
        pytest.fail(f"伺服器在埠號 {port} 上未能於 10 秒內啟動。")

    for _ in range(10):
        if db_path.exists():
            break
        time.sleep(0.2)
    if not db_path.exists():
        pytest.fail(f"測試資料庫 {db_path} 未能在 2 秒內被伺服器建立。")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    log_data = [
        (datetime.now(timezone.utc).isoformat(), 'INFO', 'TestSetup', '日誌過濾測試 - 資訊'),
        (datetime.now(timezone.utc).isoformat(), 'SUCCESS', 'TestSetup', '日誌過濾測試 - 成功'),
        (datetime.now(timezone.utc).isoformat(), 'ERROR', 'TestSetup', '日誌過濾測試 - 錯誤'),
        (datetime.now(timezone.utc).isoformat(), 'BATTLE', 'TestSetup', '日誌過濾測試 - 戰鬥'),
        (datetime.now(timezone.utc).isoformat(), 'CMD', 'TestSetup', '日誌過濾測試 - 命令'),
        (datetime.now(timezone.utc).isoformat(), 'CRITICAL', 'TestSetup', '日誌過濾測試 - 嚴重'),
        (datetime.now(timezone.utc).isoformat(), 'LOG_SHELL', 'TestSetup', '日誌過濾測試 - 殼層')
    ]
    cursor.executemany(
        "INSERT INTO logs (timestamp, level, source, message) VALUES (?, ?, ?, ?)",
        log_data
    )
    conn.commit()
    conn.close()

    yield {"port": port, "config_path": config_path, "base_url": f"http://127.0.0.1:{port}"}

    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    shutil.rmtree(tmp_test_dir)

# ==============================================================================
# 3. TEST CASES - 從各個測試檔案合併而來
# ==============================================================================

# ------------------------------------------------------------------------------
# 來源: tests/e2e/test_full_lifecycle.py
# ------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def setup_e2e_environment():
    """(Fixture) 設定 E2E 測試環境。"""
    PROJECT_ROOT_E2E = Path(__file__).resolve().parents[1]
    TMP_E2E_DIR = PROJECT_ROOT_E2E / "tmp_e2e_test_v3"
    PROJECT_FOLDER_NAME = "WEB1_E2E_TEST"

    if TMP_E2E_DIR.exists():
        shutil.rmtree(TMP_E2E_DIR)
    project_path = TMP_E2E_DIR / PROJECT_FOLDER_NAME
    project_path.mkdir(parents=True, exist_ok=True)

    shutil.copytree(PROJECT_ROOT_E2E / "src", project_path / "src")
    shutil.copytree(PROJECT_ROOT_E2E / "scripts", project_path / "scripts")
    shutil.copytree(PROJECT_ROOT_E2E / "requirements", project_path / "requirements")
    shutil.copy(PROJECT_ROOT_E2E / "pyproject.toml", project_path / "pyproject.toml")
    shutil.copy(PROJECT_ROOT_E2E / "wolf.html", project_path / "wolf.html")

    try:
        VENV_NAME = ".venv_colab_backend"
        subprocess.run([sys.executable, "-m", "venv", VENV_NAME], cwd=project_path, check=True)
        pip_path = project_path / VENV_NAME / "bin" / "pip"
        requirements_path = project_path / "requirements" / "base.txt"
        subprocess.run([str(pip_path), "install", "-r", str(requirements_path)], cwd=project_path, check=True)
        subprocess.run([str(pip_path), "install", "-e", "."], cwd=project_path, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        pytest.fail(f"在 fixture 中設定虛擬環境失敗: {e}")

    yield project_path
    shutil.rmtree(TMP_E2E_DIR)

def test_full_lifecycle(setup_e2e_environment):
    """執行完整的端對端生命週期測試（Live Server 模式）。"""
    project_path = setup_e2e_environment
    port = find_free_port()
    config_data = {"system_settings": {"timezone": "UTC"}, "__test_port__": port}
    config_path = project_path / "test_config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    command = [
        sys.executable, str(project_path / "scripts" / "run_server_only.py"),
        "--config", str(config_path)
    ]
    test_env = os.environ.copy()
    test_env["PYTHONUNBUFFERED"] = "1"
    test_env["PYTHONPATH"] = str(project_path)
    server_process = subprocess.Popen(
        command, cwd=project_path, env=test_env, stdout=sys.stdout,
        stderr=sys.stderr, text=True, encoding='utf-8'
    )

    is_ready = False
    try:
        start_time = time.time()
        while time.time() - start_time < 120:
            if server_process.poll() is not None:
                pytest.fail("伺服器提前崩潰。")
            try:
                with httpx.Client() as client:
                    response = client.get(f"http://127.0.0.1:{port}/", timeout=1)
                    if response.status_code == 200:
                        is_ready = True
                        break
            except httpx.RequestError:
                time.sleep(2)
        if not is_ready:
            pytest.fail("伺服器在 120s 內未能啟動。")
    finally:
        if server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()

# ------------------------------------------------------------------------------
# 來源: tests/e2e/test_linux_runner.py
# ------------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def cleanup_logs():
    """一個在測試前後清理日誌檔案的 fixture。"""
    LOG_DB = os.path.join(Path(__file__).resolve().parents[1], "logs.sqlite")
    LOG_ARCHIVE_DIR = os.path.join(Path(__file__).resolve().parents[1], "作戰日誌歸檔")
    if os.path.exists(LOG_DB):
        os.remove(LOG_DB)
    if os.path.exists(LOG_ARCHIVE_DIR):
        shutil.rmtree(LOG_ARCHIVE_DIR)
    yield
    if os.path.exists(LOG_DB):
        os.remove(LOG_DB)
    if os.path.exists(LOG_ARCHIVE_DIR):
        shutil.rmtree(LOG_ARCHIVE_DIR)

def test_runner_lifecycle_and_graceful_shutdown():
    """測試 linux_RUN.py 的完整生命週期"""
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    RUNNER_SCRIPT = PROJECT_ROOT / "scripts" / "local_run.py"
    assert os.path.exists(RUNNER_SCRIPT)
    command = [sys.executable, RUNNER_SCRIPT, "--fast-run"]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding='utf-8', preexec_fn=os.setsid if sys.platform != "win32" else None
    )
    try:
        time.sleep(3)
        assert process.poll() is None, "程序在測試期間意外提前終止。"
        if sys.platform != "win32":
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
        else:
            process.send_signal(signal.CTRL_C_EVENT)
        stdout, stderr = process.communicate(timeout=10)
        if "Traceback" in stderr:
            assert "KeyboardInterrupt" in stderr
        assert "Error" not in stderr
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()

# ------------------------------------------------------------------------------
# 來源: tests/integration/test_api_colab_simulation.py
# ------------------------------------------------------------------------------
def create_config_for_api_test(path: Path, log_levels: dict):
    config = {"log_settings": {"levels": log_levels}}
    with open(path, "w") as f:
        json.dump(config, f)

def test_api_reachability(live_server):
    """測試案例 1: 驗證伺服器是否成功啟動且根目錄可訪問。"""
    base_url = live_server["base_url"]
    try:
        response = httpx.get(f"{base_url}/", timeout=10)
        response.raise_for_status()
        assert "text/html" in response.headers["content-type"]
    except httpx.RequestError as e:
        pytest.fail(f"API 可及性測試失敗: {e}")
    except httpx.HTTPStatusError as e:
        pytest.fail(f"API 可及性測試失敗: {e.response.status_code}")

@pytest.mark.parametrize("enabled_levels, expected_levels", [
    ({"INFO": True, "SUCCESS": True, "ERROR": True, "BATTLE": True, "CMD": True, "CRITICAL": True, "LOG_SHELL": True},
     {"INFO", "SUCCESS", "ERROR", "BATTLE", "CMD", "CRITICAL", "LOG_SHELL"}),
    ({"INFO": False, "SUCCESS": False, "ERROR": True, "BATTLE": True, "CMD": False, "CRITICAL": True, "LOG_SHELL": False},
     {"ERROR", "BATTLE", "CRITICAL"}),
    ({"INFO": False, "SUCCESS": False, "ERROR": False, "BATTLE": False, "CMD": False, "CRITICAL": False, "LOG_SHELL": False},
     set())
])
def test_log_filtering_logic_api(live_server, enabled_levels, expected_levels):
    """測試案例 2: 系統性地驗證後端日誌過濾功能。"""
    api_url = f"{live_server['base_url']}/api/v1/status/dashboard"
    config_path = live_server["config_path"]
    create_config_for_api_test(config_path, enabled_levels)
    time.sleep(0.2)
    try:
        response = httpx.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        pytest.fail(f"API 請求失敗: {e}")
    returned_levels = {log["level"] for log in data.get("logs", [])}
    assert returned_levels == expected_levels

def test_heartbeat_is_updating(live_server):
    """測試案例 3: 驗證後端服務是真的「活著」。"""
    api_url = f"{live_server['base_url']}/api/v1/status/dashboard"
    try:
        response1 = httpx.get(api_url, timeout=5)
        response1.raise_for_status()
        data1 = response1.json()
        assert data1["current_stage"] == "服務運行中"
        time.sleep(6)
        response2 = httpx.get(api_url, timeout=5)
        response2.raise_for_status()
        data2 = response2.json()
        assert data2["current_stage"] == "服務運行中"
        assert len(data2.get("logs", [])) >= len(data1.get("logs", []))
    except Exception as e:
        pytest.fail(f"心跳測試執行時發生錯誤: {e}")

# ------------------------------------------------------------------------------
# 來源: tests/integration/test_log_filtering.py
# ------------------------------------------------------------------------------
def create_config_for_log_filter_test(path: Path, log_levels: dict):
    config = {"log_settings": {"levels": log_levels}}
    with open(path, "w") as f:
        json.dump(config, f)

@pytest.mark.parametrize("enabled_levels, expected_levels", [
    ({"INFO": True, "SUCCESS": False, "ERROR": True, "BATTLE": False, "CMD": False}, {"INFO", "ERROR"}),
    ({"INFO": True, "SUCCESS": True, "ERROR": True, "BATTLE": True, "CMD": True}, {"INFO", "SUCCESS", "ERROR", "BATTLE", "CMD"}),
    ({"INFO": False, "SUCCESS": False, "ERROR": False, "BATTLE": False, "CMD": False}, set()),
    ({"BATTLE": True}, {"BATTLE"})
])
def test_log_filtering(live_server, enabled_levels, expected_levels):
    """測試 API 是否根據 config.json 中的設定正確過濾日誌。"""
    port = live_server["port"]
    config_path = live_server["config_path"]
    create_config_for_log_filter_test(config_path, enabled_levels)
    time.sleep(0.1)
    api_url = f"http://127.0.0.1:{port}/api/v1/status/dashboard"
    try:
        response = httpx.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except (httpx.RequestError, json.JSONDecodeError) as e:
        pytest.fail(f"API 請求失敗: {e}")
    assert "logs" in data
    returned_levels = {log["level"] for log in data["logs"]}
    assert returned_levels == expected_levels

# ------------------------------------------------------------------------------
# 來源: tests/test_db_queries.py
# ------------------------------------------------------------------------------
from phoenix_core.db_queries import query_logs_by_level

def test_query_success_logs(mock_db):
    results = query_logs_by_level(mock_db, 'SUCCESS', limit=10)
    assert len(results) == 3
    for row in results:
        assert row[2] == 'SUCCESS'

def test_query_error_logs(mock_db):
    results = query_logs_by_level(mock_db, 'ERROR', limit=10)
    assert len(results) == 2
    for row in results:
        assert row[2] == 'ERROR'

def test_query_non_existent_level(mock_db):
    results = query_logs_by_level(mock_db, 'CRITICAL', limit=10)
    assert len(results) == 0

def test_query_with_limit(mock_db):
    results = query_logs_by_level(mock_db, 'SUCCESS', limit=1)
    assert len(results) == 1

# ------------------------------------------------------------------------------
# 來源: tests/test_fixtures.py
# ------------------------------------------------------------------------------
def test_mock_report_files_creation(mock_report_files):
    reports_path = mock_report_files / "reports"
    assert reports_path.exists()
    assert (reports_path / "summary_report.md").exists()
    assert (reports_path / "detailed_log_report.md").exists()
    assert (reports_path / "performance_report.md").exists()
    summary_content = (reports_path / "summary_report.md").read_text()
    assert summary_content == "這是總結報告。"

# ------------------------------------------------------------------------------
# 來源: tests/test_report_generator.py
# ------------------------------------------------------------------------------
from phoenix_core.report_generator import read_selected_reports, archive_selected_reports

def test_read_selected_reports(mock_report_files):
    reports_dir = mock_report_files / "reports"
    selection = ['summary_report.md', 'performance_report.md']
    result = read_selected_reports(reports_dir, selection)
    assert "這是總結報告。" in result
    assert "這是效能報告。" in result
    assert "這是詳細日誌報告。" not in result
    assert "\n\n---\n\n" in result

def test_read_selected_reports_empty_selection(mock_report_files):
    reports_dir = mock_report_files / "reports"
    selection = []
    result = read_selected_reports(reports_dir, selection)
    assert result == ""

def test_read_selected_reports_file_not_found(mock_report_files):
    reports_dir = mock_report_files / "reports"
    selection = ['summary_report.md', 'non_existent_report.md']
    result = read_selected_reports(reports_dir, selection)
    assert "這是總結報告。" in result
    assert "non_existent_report" not in result

def test_archive_selected_reports(mock_report_files):
    source_reports_dir = mock_report_files / "reports"
    archive_root_dir = mock_report_files
    selection = ['detailed_log_report.md', 'summary_report.md']
    new_archive_path = archive_selected_reports(source_reports_dir, archive_root_dir, selection)
    assert new_archive_path.parent.name == "報告"
    assert (archive_root_dir / "報告").exists()
    assert new_archive_path.exists()
    archived_files = list(os.listdir(new_archive_path))
    assert len(archived_files) == 2
    assert "detailed_log_report.md" in archived_files
    assert "summary_report.md" in archived_files

# ------------------------------------------------------------------------------
# 來源: tests/test_watchdog.py
# ------------------------------------------------------------------------------
from phoenix_core.watchdog import check_heartbeat_status, HEARTBEAT_KEY

def test_heartbeat_ok(mock_db):
    status = check_heartbeat_status(mock_db, threshold_seconds=15)
    assert status == 'OK'

def test_heartbeat_expired(mock_db):
    expired_ts = (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat()
    cursor = mock_db.cursor()
    cursor.execute("UPDATE status_updates SET timestamp = ? WHERE key = ?", (expired_ts, HEARTBEAT_KEY))
    mock_db.commit()
    status = check_heartbeat_status(mock_db, threshold_seconds=60)
    assert status == 'STOPPED'

def test_heartbeat_not_found(mock_db):
    cursor = mock_db.cursor()
    cursor.execute("DELETE FROM status_updates WHERE key = ?", (HEARTBEAT_KEY,))
    mock_db.commit()
    status = check_heartbeat_status(mock_db, threshold_seconds=15)
    assert status == 'NOT_FOUND'

# ------------------------------------------------------------------------------
# 來源: tests/unit/phoenix_core/kernel/test_package_utils.py
# ------------------------------------------------------------------------------
from phoenix_core.kernel.package_utils import get_package_size, parse_package_spec

@pytest.mark.parametrize("spec, expected_name, expected_version", [
    ("fastapi==0.116.1", "fastapi", "0.116.1"),
    ("psutil", "psutil", None),
    ("uvicorn[standard]==0.35.0", "uvicorn", "0.35.0"),
])
def test_parse_package_spec(spec, expected_name, expected_version):
    name, version = parse_package_spec(spec)
    assert name == expected_name
    assert version == expected_version

@pytest.fixture
def mock_httpx_client():
    return MagicMock(spec=httpx.Client)

def test_get_package_size_success_specific_version(mock_httpx_client):
    spec = "my-package==1.2.3"
    json_payload = {"releases": {"1.2.3": [{"size": 100}, {"size": 200}]}}
    mock_httpx_client.get.return_value = create_mock_response(json_payload)
    size = get_package_size(spec, mock_httpx_client)
    assert size == 300

def test_get_package_size_success_latest_version(mock_httpx_client):
    spec = "my-package"
    json_payload = {"info": {"version": "2.0.0"}, "releases": {"1.0.0": [{"size": 50}], "2.0.0": [{"size": 500}, {"size": 500}]}}
    mock_httpx_client.get.return_value = create_mock_response(json_payload)
    size = get_package_size(spec, mock_httpx_client)
    assert size == 1000

def test_get_package_size_package_not_found(mock_httpx_client):
    spec = "non-existent-package==1.0"
    mock_httpx_client.get.return_value = create_mock_response({}, status_code=404)
    size = get_package_size(spec, mock_httpx_client)
    assert size == 0

def create_mock_response(json_data, status_code=200):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    def raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError(message=f"HTTP Error {status_code}", request=MagicMock(), response=mock_response)
    mock_response.raise_for_status = MagicMock(side_effect=raise_for_status)
    return mock_response

# ------------------------------------------------------------------------------
# 來源: tests/unit/phoenix_core/modules/test_dataprovider.py
# ------------------------------------------------------------------------------
MODULE_PATH_TO_MOCK = "src.phoenix_core.modules.dataprovider.logic.storage"

@pytest.mark.timeout(1)
def test_stock_data_cache_hit(monkeypatch):
    def mock_load_json(file_name):
        return {"symbol": "TSMC", "price": 123.45, "timestamp": "cached_time"}
    monkeypatch.setattr(f"{MODULE_PATH_TO_MOCK}.load_json", mock_load_json)
    from phoenix_core.main import app
    with TestClient(app) as client:
        response = client.get("/data/stock/TSMC")
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 123.45

@pytest.mark.timeout(1)
def test_stock_data_cache_miss(monkeypatch):
    monkeypatch.setattr(f"{MODULE_PATH_TO_MOCK}.load_json", lambda fn: None)
    monkeypatch.setattr(f"{MODULE_PATH_TO_MOCK}.save_json", lambda fn, data: None)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    from phoenix_core.main import app
    with TestClient(app) as client:
        response = client.get("/data/stock/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
