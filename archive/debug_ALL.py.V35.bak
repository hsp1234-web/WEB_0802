# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║    🔍 全機能自動化偵錯腳本 V2.4 - 最終版                           ║
# ║              (檔案: debug/debug_ALL.py)                            ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI)                                                 ║
# ║   - V2.4 更新:                                                     ║
# ║       - 修復所有已知 bug，包括 git clone、環境變數、模組導入等。   ║
# ║       - 整合了優雅關機與自我引導機制，確保測試流程的穩定性。       ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import threading
import time
import shutil
import sqlite3
import importlib
import json
import signal
from pathlib import Path

# --- 系統路徑設定 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- 全域設定 ---
GIT_REPO = "https://github.com/hsp1234-web/WEB_0802.git"
GIT_BRANCH = "0.4.9"
VENV_DIR = Path("./.venv_debug")
VENV_PYTHON = VENV_DIR / "bin" / "python" if os.name != 'nt' else VENV_DIR / "Scripts" / "python.exe"
REQUIREMENTS_FILE_DEV = Path("./requirements/dev.txt")
WATCHDOG_TIMEOUT = 60.0
TEMP_CONFIG_FILE = Path("./temp_config_for_test.json")

# --- 全域狀態變數 ---
server_process = None
watchdog_timer = None

def print_header(phase, title):
    header_text = f"階段 {phase}: {title}"
    print("\n" + "="*80)
    print(f"🚀 {time.strftime('%Y-%m-%d %H:%M:%S')} - {header_text}")
    print("="*80)

def run_command(command, cwd=".", check=True, env=None, quiet=False):
    if not quiet: print(f"   🔹 執行命令: {' '.join(map(str, command))}")

    # 正確的環境變數處理邏輯
    current_env = os.environ.copy()
    if env:
        current_env.update({k: str(v) for k, v in env.items()})

    try:
        process = subprocess.run(
            command, capture_output=True, text=True, encoding='utf-8',
            cwd=str(cwd), check=check, env=current_env
        )
        if not quiet:
            if process.stdout: print(f"     [STDOUT] {process.stdout.strip()}")
            if process.stderr: print(f"     [STDERR] {process.stderr.strip()}")
        return process
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        if e.stdout: print(f"   [失敗的 STDOUT]:\n{e.stdout}", file=sys.stderr)
        if e.stderr: print(f"   [失敗的 STDERR]:\n{e.stderr}", file=sys.stderr)
        raise

def handle_timeout():
    global server_process
    print(f"🔥🔥🔥 看門狗觸發！在 {WATCHDOG_TIMEOUT} 秒內未偵測到成功啟動訊息。🔥🔥🔥", file=sys.stderr)
    if server_process and server_process.poll() is None: server_process.kill()
    raise TimeoutError("伺服器啟動超時")

def reset_watchdog():
    global watchdog_timer
    if watchdog_timer: watchdog_timer.cancel()
    watchdog_timer = threading.Timer(WATCHDOG_TIMEOUT, handle_timeout)
    watchdog_timer.start()

def phase_1_validate_download_channel():
    print_header(1, "下載通道驗證")
    temp_clone_dir = Path("./temp_clone_dir_for_validation")
    if temp_clone_dir.exists(): shutil.rmtree(temp_clone_dir)
    try:
        run_command(["git", "clone", "--branch", GIT_BRANCH, GIT_REPO, str(temp_clone_dir)], quiet=True)
        assert (temp_clone_dir / "README.md").exists()
    finally:
        if temp_clone_dir.exists(): shutil.rmtree(temp_clone_dir)
    print("✅ 階段一 PASS: 下載通道驗證成功。")

def phase_2_backend_health_check(config: dict):
    global server_process, watchdog_timer
    print_header(2, f"後端基礎健康檢查 (設定: {config.get('name', 'default')})")
    with open(TEMP_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config.get('settings', {}), f, indent=4)
    env = {"PHOENIX_CONFIG_PATH": str(TEMP_CONFIG_FILE), "PYTHONUNBUFFERED": "1"}
    command = [str(VENV_PYTHON), "-m", "uvicorn", "src.phoenix_core.main:app", "--host", "127.0.0.1", "--port", "8088", "--log-level", "info"]
    server_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1, env=env)
    print(f"✅ 伺服器程序已啟動 (PID: {server_process.pid})。")
    reset_watchdog()
    try:
        for line in iter(server_process.stdout.readline, ''):
            if not line: break
            print(f"   [API Server] {line.strip()}")
            reset_watchdog()
            if "Application startup complete" in line:
                if watchdog_timer: watchdog_timer.cancel()
                print("✅ 階段二 PASS: 後端基礎健康檢查成功。")
                return
        output, _ = server_process.communicate()
        print(f"❌ 伺服器意外終止，輸出:\n{output}", file=sys.stderr)
        raise RuntimeError("伺服器日誌流結束，但未偵測到成功啟動訊息。")
    except TimeoutError:
        raise

def phase_3_database_preparation():
    print_header(3, "資料庫準備流程驗證")
    db_path = Path("./state.db")
    renamed_db_path = Path("./logs.sqlite")
    assert db_path.exists(), f"前置步驟失敗，找不到 '{db_path}'"
    if renamed_db_path.exists(): renamed_db_path.unlink()
    wal_file = Path(f"{db_path}-wal")
    shm_file = Path(f"{db_path}-shm")
    if wal_file.exists(): shutil.copy(wal_file, Path(f"{renamed_db_path}-wal"))
    if shm_file.exists(): shutil.copy(shm_file, Path(f"{renamed_db_path}-shm"))
    shutil.move(str(db_path), str(renamed_db_path))
    assert renamed_db_path.exists() and not db_path.exists()
    print("✅ 階段三 PASS: 資料庫準備流程驗證成功。")

def phase_4_parameter_verification(config: dict):
    print_header(4, f"參數驗證 (設定: {config.get('name', 'default')})")
    log_settings = config.get('settings', {}).get('log_settings', {})
    if not log_settings:
        expected_levels = {'BATTLE', 'SUCCESS', 'INFO', 'CMD', 'LOG_SHELL', 'ERROR', 'CRITICAL'}
    else:
        expected_levels = {level.upper() for level, enabled in log_settings.items() if enabled}
    conn = sqlite3.connect(Path("./logs.sqlite"))
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT level FROM logs")
    found_levels = {row[0].upper() for row in cursor.fetchall()}
    conn.close()
    print(f"   - 預期寫入的日誌等級: {sorted(list(expected_levels)) if expected_levels else '無'}")
    print(f"   - 資料庫中實際找到的日誌等級: {sorted(list(found_levels)) if found_levels else '無'}")
    assert found_levels == expected_levels, f"日誌等級不匹配！預期: {expected_levels}, 實際: {found_levels}"
    print("✅ 階段四 PASS: 參數驗證成功。")

def phase_5_report_module_validation():
    print_header(5, "報告模組核心功能驗證")
    from src.phoenix_core.report_generator import read_selected_reports, archive_selected_reports
    reports_dir, archive_dir = Path("./temp_reports"), Path("./temp_archive")
    reports_dir.mkdir(exist_ok=True); archive_dir.mkdir(exist_ok=True)
    (reports_dir / "r1.md").write_text("report1")
    (reports_dir / "r2.md").write_text("report2")
    assert "report1" in read_selected_reports(reports_dir, ["r1.md"])
    new_archive = archive_selected_reports(reports_dir, archive_dir, ["r2.md"])
    assert (new_archive / "r2.md").exists()
    shutil.rmtree(reports_dir); shutil.rmtree(archive_dir)
    print("✅ 階段五 PASS: 報告模組核心功能驗證成功。")

def full_test_run(config: dict):
    global server_process
    try:
        phase_2_backend_health_check(config)
        print("   ✅ 後端已啟動，等待 2 秒以確保日誌寫入...")
        time.sleep(2)
        print("   優雅地關閉伺服器以確保資料庫檔案完整...")
        server_process.send_signal(signal.SIGINT)
        server_process.wait(timeout=10)
        print("   ✅ 伺服器已關閉。")
        phase_3_database_preparation()
        phase_4_parameter_verification(config)
    finally:
        if server_process and server_process.poll() is None:
            server_process.kill()
        db_files = ["state.db", "logs.sqlite", "state.db-shm", "state.db-wal", "logs.sqlite-wal", "logs.sqlite-shm"]
        for f in db_files:
            if Path(f).exists(): Path(f).unlink(missing_ok=True)
        if TEMP_CONFIG_FILE.exists(): TEMP_CONFIG_FILE.unlink(missing_ok=True)
        print("--- 單次測試流程清理完畢 ---")

def main():
    if not (sys.prefix == str(VENV_DIR.resolve())):
        print_header(0, "環境預備 (外部)")
        if VENV_DIR.exists(): shutil.rmtree(VENV_DIR)
        run_command([sys.executable, "-m", "venv", str(VENV_DIR)])
        run_command([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE_DEV)])
        print("\n--- 環境準備完畢，正在使用 venv 的 Python 重新啟動本腳本 ---")
        result = subprocess.run([str(VENV_PYTHON), __file__])
        sys.exit(result.returncode)

    print_header("🚀", "啟動全功能自動化偵錯腳本 (VENV 內)")
    phase_1_validate_download_channel()
    test_configs = [
        {"name": "預設設定", "settings": {}},
        {"name": "僅錯誤日誌", "settings": {"log_settings": {"BATTLE": False, "SUCCESS": False, "INFO": False, "CMD": False, "LOG_SHELL": False, "ERROR": True, "CRITICAL": True, "PERF": False}}},
        {"name": "僅 BATTLE 日誌", "settings": {"log_settings": {"BATTLE": True, "ERROR": False, "INFO": False, "LOG_SHELL": False, "SUCCESS": False, "CMD": False, "CRITICAL": False, "PERF": False}}}
    ]
    for i, config in enumerate(test_configs):
        print("\n" + "#"*80 + f"\n### 開始第 {i+1}/{len(test_configs)} 組參數化測試: {config['name']} ###\n" + "#"*80)
        full_test_run(config)
    phase_5_report_module_validation()
    print("\n" + "🎉"*20 + "\n🎉 恭喜！所有偵錯階段及參數化測試已全部成功通過！ 🎉\n" + "🎉"*20)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"\n❌ 偵錯流程執行失敗: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        if sys.prefix == str(VENV_DIR.resolve()):
            print("\n" + "="*80 + "\n🧹 正在執行最終清理...\n" + "="*80)
            if VENV_DIR.exists(): shutil.rmtree(VENV_DIR, ignore_errors=True)
            print("✅ 最終清理完成。")
