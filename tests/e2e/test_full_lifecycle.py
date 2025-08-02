# 檔案: tests/e2e/test_full_lifecycle.py
# 說明: (V2) 模擬從啟動到報告的完整使用者流程，以進行端對端驗證。
#      此版本利用環境變數進行配置，無需修改原始碼。
import subprocess
import sys
import os
import time
import shutil
from pathlib import Path
import pytest

# --- 測試設定 ---
# 將PROJECT_ROOT設定為此檔案所在目錄往上兩層的目錄
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 在專案根目錄下建立一個名為 `tmp_e2e_test_v2` 的臨時目錄
TMP_E2E_DIR = PROJECT_ROOT / "tmp_e2e_test_v2"
# 設定專案資料夾的名稱
PROJECT_FOLDER_NAME = "WEB1_E2E_TEST"
# 組合出完整的專案路徑
PROJECT_PATH = TMP_E2E_DIR / PROJECT_FOLDER_NAME
# 模擬 `colab_runner.py` 運行的時間（秒）
RUN_TIME_SECONDS = 15

@pytest.fixture(scope="module")
def setup_e2e_environment():
    """
    (Fixture) 設定 E2E 測試環境。
    在所有測試開始前執行一次，並在結束後進行清理。
    """
    # --- 環境準備 ---
    # 如果臨時目錄已存在，先刪除
    if TMP_E2E_DIR.exists():
        shutil.rmtree(TMP_E2E_DIR)
    # 建立臨時目錄
    TMP_E2E_DIR.mkdir()

    # --- 模擬的 Colab 內容目錄 ---
    # 這是 `colab_runner.py` 和 `report.py` 將要操作的根目錄
    # 我們將其命名為 `content` 以模擬 Colab 的環境
    content_dir = TMP_E2E_DIR / "content"
    content_dir.mkdir()

    # --- 複製專案程式碼 ---
    # 將當前的專案完整複製到臨時的專案路徑下
    # 忽略 .venv, .git 等不必要的檔案
    shutil.copytree(
        PROJECT_ROOT,
        PROJECT_PATH,
        ignore=shutil.ignore_patterns('.venv', '.git', '__pycache__', 'tmp_e2e_test*')
    )

    # `yield` 關鍵字將控制權交還給測試函式
    # `yield` 之後的程式碼將在測試結束後執行
    yield {
        "content_dir": content_dir,
        "project_path": PROJECT_PATH
    }

    # --- 清理 ---
    # 測試結束後，刪除整個臨時目錄
    shutil.rmtree(TMP_E2E_DIR)
    print("\n[INFO] 臨時 E2E 測試環境已清理。")

def test_full_lifecycle(setup_e2e_environment):
    """
    執行完整的端對端生命週期測試。
    """
    # 從 fixture 取得設定好的路徑
    content_dir = setup_e2e_environment["content_dir"]
    project_path = setup_e2e_environment["project_path"]

    # --- 1. 設定環境變數 ---
    # 這是新測試方法的關鍵：透過環境變數控制腳本行為
    test_env = os.environ.copy()
    test_env["PHOENIX_FAST_TEST_MODE"] = "True"
    test_env["PHOENIX_CONTENT_ROOT"] = str(content_dir)
    test_env["PHOENIX_PROJECT_FOLDER"] = PROJECT_FOLDER_NAME
    # 將專案根目錄添加到 PYTHONPATH，以便子程序能找到 'src' 模組
    test_env["PYTHONPATH"] = str(project_path) + os.pathsep + test_env.get("PYTHONPATH", "")

    # --- 2. 執行 colab_runner.py ---
    # 我們不再需要修改 runner 腳本，只需在正確的環境下執行它
    colab_runner_path = project_path / "run" / "colab_runner.py"
    # 使用 `sys.executable` 確保我們用的是執行 pytest 的同一個 Python 解譯器
    command = [sys.executable, str(colab_runner_path)]

    print(f"\n[INFO] 執行指令: {' '.join(command)}")
    print(f"[INFO] 環境變數: PHOENIX_CONTENT_ROOT={test_env['PHOENIX_CONTENT_ROOT']}, PHOENIX_PROJECT_FOLDER={test_env['PHOENIX_PROJECT_FOLDER']}")

    # 啟動子程序
    process = subprocess.Popen(
        command,
        env=test_env,
        cwd=project_path, # 在模擬的專案目錄下執行
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # --- 3. 等待並優雅關閉 ---
    print(f"[INFO] 等待 {RUN_TIME_SECONDS} 秒...")
    time.sleep(RUN_TIME_SECONDS)

    print(f"[INFO] 發送 SIGINT (Ctrl+C) 至進程 (PID: {process.pid}) 以觸發優雅關機...")
    # process.send_signal(signal.SIGINT) # 在某些 CI 環境中可能不穩定
    process.terminate() # 使用 terminate 更為可靠
    try:
        process.wait(timeout=20)
        print("[INFO] colab_runner.py 進程已結束。")
    except subprocess.TimeoutExpired:
        print("[WARN] 等待進程超時，強制終止。")
        process.kill()

    # --- 4. 驗證 state.db 是否生成 ---
    db_path = project_path / "state.db"
    assert db_path.exists(), f"測試失敗: state.db 未在 {db_path} 中生成。"
    print(f"[INFO] ✅ 成功找到 state.db 於: {db_path}")

    # --- 5. 執行 report.py ---
    report_script_path = project_path / "run" / "report.py"
    report_command = [sys.executable, str(report_script_path)]

    print(f"[INFO] 執行報告生成指令: {' '.join(report_command)}")
    report_result = subprocess.run(
        report_command,
        env=test_env, # 同樣使用設定好的環境變數
        cwd=project_path,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    # 印出報告腳本的輸出，方便除錯
    print("\n--- report.py STDOUT ---")
    print(report_result.stdout)
    if report_result.stderr:
        print("\n--- report.py STDERR ---")
        print(report_result.stderr)

    assert report_result.returncode == 0, "測試失敗: run/report.py 執行時返回非零代碼。"

    # --- 6. 最終驗證報告檔案 ---
    reports_dir = project_path / "reports"
    assert reports_dir.is_dir(), f"報告目錄 {reports_dir} 未被建立。"

    expected_reports = [
        "summary_report.md",
        "performance_report.md",
        "detailed_log_report.md"
    ]
    for report_name in expected_reports:
        report_path = reports_dir / report_name
        assert report_path.exists(), f"預期的報告檔案 {report_name} 未在 {reports_dir} 中找到。"
        print(f"[INFO] ✅ 成功驗證報告存在: {report_name}")

    print("\n🎉 [SUCCESS] 端對端生命週期測試成功！")
