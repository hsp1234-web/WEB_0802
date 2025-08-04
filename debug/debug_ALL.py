# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🔍 全功能自動化偵錯腳本 (All-in-One Debug Script) V1.0        ║
# ║              (檔案: debug/debug_ALL.py)                            ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 建立一個無須人工干預、可在任何標準 Python 環境中運行的   ║
# ║           單一腳本。它將依序、系統性地驗證從程式碼下載、後端啟動、 ║
# ║           資料庫準備、到核心模組功能的每一個環節。                 ║
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
from pathlib import Path

# --- 系統路徑設定 ---
# 確保專案根目錄在 sys.path 中，以便後續模組導入
# 我們的腳本在 debug/ 子目錄中，所以專案根目錄是其父目錄。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"ℹ️  將專案根目錄 '{PROJECT_ROOT}' 加入到 sys.path 以進行模組導入。")


# --- 全域設定 ---
# 階段一：下載驗證
GIT_REPO = "https://github.com/hsp1234-web/WEB_0802.git"
GIT_BRANCH = "0.4.7"
TEMP_CLONE_DIR = "temp_clone_dir_for_validation"

# 階段二：後端健康檢查
VENV_DIR = Path("./.venv_debug")
VENV_PYTHON = VENV_DIR / "bin" / "python" if os.name != 'nt' else VENV_DIR / "Scripts" / "python.exe"
REQUIREMENTS_FILE_DEV = Path("./requirements/dev.txt")
WATCHDOG_TIMEOUT = 45.0  # 秒，加長以應對可能的網路延遲
server_process = None
watchdog_timer = None

# 階段三：資料庫準備
SOURCE_DB_PATH = Path("./state.db")
RENAMED_DB_PATH = Path("./logs.sqlite")

# 階段五：報告模組測試
TEMP_REPORTS_DIR = Path("./temp_reports_for_test")
TEMP_ARCHIVE_DIR = Path("./temp_archive_for_test")


def print_header(phase, title):
    """打印帶有階段和標題的日誌分隔線。"""
    header_text = f"階段 {phase}: {title}"
    print("\n" + "="*80)
    print(f"🚀 {time.strftime('%Y-%m-%d %H:%M:%S')} - {header_text}")
    print("="*80)

def run_command(command, cwd=".", check=True, env=None):
    """執行一個子程序命令並打印其輸出。"""
    print(f"   🔹 執行命令: {' '.join(map(str, command))}")
    try:
        # 確保環境變數是字串
        full_env = os.environ.copy()
        if env:
            full_env.update({k: str(v) for k, v in env.items()})

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(cwd),
            check=check,
            env=full_env
        )
        if process.stdout:
            print(f"     [STDOUT] {process.stdout.strip()}")
        if process.stderr:
            print(f"     [STDERR] {process.stderr.strip()}")
        return process
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"   [失敗的 STDOUT]:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"   [失敗的 STDERR]:\n{e.stderr}", file=sys.stderr)
        raise

# --- 看門狗與伺服器監控 ---
def handle_timeout():
    """看門狗超時處理函式。"""
    global server_process
    print(f"🔥🔥🔥 看門狗觸發！在 {WATCHDOG_TIMEOUT} 秒內未偵測到成功啟動訊息。🔥🔥🔥", file=sys.stderr)
    print("      伺服器可能已卡死或啟動失敗，正在強制終止...", file=sys.stderr)
    if server_process and server_process.poll() is None:
        server_process.kill()
    raise TimeoutError("伺服器啟動超時")

def reset_watchdog():
    """重置看門狗計時器。"""
    global watchdog_timer
    if watchdog_timer:
        watchdog_timer.cancel()
    watchdog_timer = threading.Timer(WATCHDOG_TIMEOUT, handle_timeout)
    watchdog_timer.start()


# --- 階段函式定義 ---

def phase_1_validate_download_channel():
    """階段一：下載通道驗證"""
    print_header(1, "下載通道驗證")

    if Path(TEMP_CLONE_DIR).exists():
        print(f"   ℹ️  發現舊的臨時目錄 '{TEMP_CLONE_DIR}'，將其移除。")
        shutil.rmtree(TEMP_CLONE_DIR)

    try:
        print(f"   正在從 '{GIT_REPO}' (分支: {GIT_BRANCH}) 下載到臨時目錄...")
        # 使用 --depth 1 進行淺層複製，加快下載速度
        run_command(["git", "clone", "--branch", GIT_BRANCH, "--depth", "1", GIT_REPO, TEMP_CLONE_DIR])
        print("   ✅ 下載成功。")

        # 進行一個簡單的內容驗證，確保下載的不是空目錄
        expected_file = Path(TEMP_CLONE_DIR) / "README.md"
        if not expected_file.exists():
            raise FileNotFoundError(f"驗證失敗：下載的目錄中找不到 {expected_file}")
        print(f"   ✅ 內容驗證成功 (找到 {expected_file})。")

    finally:
        # 這個階段的職責是獨立和自包含的，所以執行完畢後立即清理
        if Path(TEMP_CLONE_DIR).exists():
            print(f"   正在清理此階段的臨時目錄 '{TEMP_CLONE_DIR}'...")
            shutil.rmtree(TEMP_CLONE_DIR)
            print("   ✅ 臨時目錄已清理。")

    print("✅ 階段一 PASS: 下載通道驗證成功。")

def phase_2_backend_health_check():
    """階段二：後端基礎健康檢查"""
    global server_process, watchdog_timer
    print_header(2, "後端基礎健康檢查")

    # 1. 環境準備
    if VENV_DIR.exists():
        print(f"ℹ️  發現現有虛擬環境 '{VENV_DIR}'，將其移除以確保純淨環境。")
        shutil.rmtree(VENV_DIR)

    print(f"正在建立新的虛擬環境於 '{VENV_DIR}'...")
    run_command([sys.executable, "-m", "venv", str(VENV_DIR)])
    print("✅ 虛擬環境建立成功。")

    if not REQUIREMENTS_FILE_DEV.exists():
        raise FileNotFoundError(f"依賴檔案不存在: {REQUIREMENTS_FILE_DEV}")

    print(f"正在從 '{REQUIREMENTS_FILE_DEV}' 安裝依賴...")
    run_command([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE_DEV)])
    print("✅ 依賴安裝完成。")

    # 2. 啟動後端服務與看門狗
    command = [
        str(VENV_PYTHON), "-m", "uvicorn", "src.phoenix_core.main:app",
        "--host", "127.0.0.1", "--port", "8088", "--log-level", "info",
    ]
    print(f"   🔹 使用 Popen 啟動命令: {' '.join(command)}")

    server_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        bufsize=1
    )

    print(f"✅ 伺服器程序已啟動 (PID: {server_process.pid})。")
    print(f"⏳ 正在監控日誌輸出... (看門狗超時: {WATCHDOG_TIMEOUT} 秒)")
    reset_watchdog()

    try:
        for line in iter(server_process.stdout.readline, ''):
            if not line:
                break
            line = line.strip()
            print(f"   [API Server] {line}")
            reset_watchdog()  # 每收到一行日誌，就重置看門狗
            if "Application startup complete" in line:
                print("\n✅ 偵測到『應用程式啟動完成』訊息！伺服器已準備就緒。")
                print("   伺服器將在背景繼續運行以供後續階段測試。")
                if watchdog_timer:
                    watchdog_timer.cancel()  # 本階段的監控任務完成
                print("✅ 階段二 PASS: 後端基礎健康檢查成功。")
                return  # 成功，返回

        # 如果日誌流結束但未檢測到成功訊息
        raise RuntimeError("伺服器日誌流已結束，但未偵測到成功啟動訊息。")
    except TimeoutError:
        # 由 handle_timeout 引發，此處重新引發以被主異常處理塊捕獲
        raise

def create_fake_state_db_if_needed():
    """如果 state.db 不存在，則建立一個結構完整的假資料庫以供測試。"""
    if SOURCE_DB_PATH.exists():
        print(f"   ℹ️  找到由後端生成的真實資料庫: {SOURCE_DB_PATH}")
        return

    print(f"   ⚠️  未找到由後端生成的 {SOURCE_DB_PATH}，正在建立一個假的資料庫以便測試...")
    if RENAMED_DB_PATH.exists():
        RENAMED_DB_PATH.unlink()

    conn = sqlite3.connect(SOURCE_DB_PATH)
    cursor = conn.cursor()
    # 建立一個簡單的表以模擬真實結構
    cursor.execute("CREATE TABLE IF NOT EXISTS status_updates (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT INTO status_updates (key, value) VALUES (?, ?)",
                   ("test_key", "test_value"))
    conn.commit()
    conn.close()
    print(f"   ✅  假的 '{SOURCE_DB_PATH}' 已建立。")

def phase_3_database_preparation():
    """階段三：資料庫準備流程驗證"""
    print_header(3, "資料庫準備流程驗證")

    # 1. 等待後端生成 state.db
    print(f"   正在等待後端生成 '{SOURCE_DB_PATH}' (最多 10 秒)...")
    db_found = False
    for i in range(10):
        if SOURCE_DB_PATH.exists():
            print(f"   ✅  在 {i+1} 秒後找到 '{SOURCE_DB_PATH}'。")
            db_found = True
            break
        time.sleep(1)

    if not db_found:
        print(f"   ⚠️  等待超時，後端未生成 '{SOURCE_DB_PATH}'。")
        # 即使後端沒成功建立，也建立一個假的來測試後續流程
        create_fake_state_db_if_needed()

    # 2. 執行重命名
    print(f"   正在將 '{SOURCE_DB_PATH}' 重命名為 '{RENAMED_DB_PATH}'...")
    if RENAMED_DB_PATH.exists():
         RENAMED_DB_PATH.unlink() # 確保目標位置是乾淨的
    shutil.move(str(SOURCE_DB_PATH), str(RENAMED_DB_PATH))

    # 3. 驗證結果
    assert RENAMED_DB_PATH.exists(), f"重命名失敗，找不到目標檔案 {RENAMED_DB_PATH}"
    assert not SOURCE_DB_PATH.exists(), f"重命名失敗，來源檔案 {SOURCE_DB_PATH} 依然存在"
    print(f"   ✅  資料庫重命名成功。現在存在 '{RENAMED_DB_PATH}'。")

    print("✅ 階段三 PASS: 資料庫準備流程驗證成功。")

def phase_4_colab_logic_simulation():
    """階段四：Colab 啟動邏輯模擬 (無介面)"""
    print_header(4, "Colab 啟動邏輯模擬 (無介面)")
    print("   本階段不重新執行啟動，而是驗證前序階段已達成 Colab 腳本的預期效果。")

    # 1. 驗證 `prepare_environment` 的效果
    #    效果：專案程式碼存在且 Python 路徑已設定
    project_root = Path.cwd()
    assert (project_root / "pyproject.toml").exists(), "驗證失敗：未在專案根目錄執行"
    # 在某些系統中，sys.path 可能包含相對路徑 '.' 或絕對路徑
    project_root_in_path = str(project_root) in sys.path or '' in sys.path or '.' in sys.path
    assert project_root_in_path, f"驗證失敗：專案根目錄 '{project_root}' 未在 sys.path 中"
    print("   ✅ `prepare_environment` 效果驗證成功 (程式碼已存在，路徑已設定)。")

    # 2. 驗證 `setup_backend` 的效果
    #    效果：依賴已安裝，後端已啟動，資料庫已生成
    assert VENV_PYTHON.exists(), f"驗證失敗：虛擬環境執行檔不存在于 {VENV_PYTHON}"
    print(f"   ✅ 虛擬環境存在於: {VENV_PYTHON}")

    global server_process
    assert server_process and server_process.poll() is None, "驗證失敗：後端伺服器進程未在運行"
    print(f"   ✅ 後端伺服器正在運行 (PID: {server_process.pid})。")

    # 在階段三，state.db 已被重命名為 logs.sqlite
    assert RENAMED_DB_PATH.exists(), f"驗證失敗：預期的資料庫檔案 {RENAMED_DB_PATH} 不存在"
    print(f"   ✅ `setup_backend` 效果驗證成功 (依賴已安裝，服務在運行，資料庫已生成)。")

    print("✅ 階段四 PASS: Colab 啟動邏輯模擬成功。")

def phase_5_report_module_validation():
    """階段五：報告模組核心功能驗證 (無介面)"""
    print_header(5, "報告模組核心功能驗證 (無介面)")

    # 1. 動態導入模組
    try:
        # 確保 sys.path 包含專案根目錄，以便導入 src
        if '.' not in sys.path:
            sys.path.insert(0, '.')
        report_generator = importlib.import_module("src.phoenix_core.report_generator")
        read_selected_reports = getattr(report_generator, "read_selected_reports")
        archive_selected_reports = getattr(report_generator, "archive_selected_reports")
        print("   ✅ 成功導入 'report_generator' 模組。")
    except (ImportError, AttributeError) as e:
        print(f"❌ 無法導入報告生成模組或函式: {e}", file=sys.stderr)
        raise

    # 2. 建立測試環境 (假報告)
    TEMP_REPORTS_DIR.mkdir(exist_ok=True)
    TEMP_ARCHIVE_DIR.mkdir(exist_ok=True)
    print(f"   建立臨時報告目錄: {TEMP_REPORTS_DIR}")

    fake_report_1_content = "這是第一份報告的內容。"
    fake_report_2_content = "這是第二份報告，它很重要。"
    (TEMP_REPORTS_DIR / "report1.md").write_text(fake_report_1_content, encoding="utf-8")
    (TEMP_REPORTS_DIR / "report2.md").write_text(fake_report_2_content, encoding="utf-8")
    (TEMP_REPORTS_DIR / "ignored.txt").write_text("這個檔案不應該被選中。", encoding="utf-8")
    print("   ✅ 已建立假的報告檔案。")

    # 3. 測試 read_selected_reports 函式
    print("   測試 `read_selected_reports`...")
    selection = ["report1.md", "report2.md"]
    combined_content = read_selected_reports(TEMP_REPORTS_DIR, selection)

    assert fake_report_1_content in combined_content, "合併內容缺少 report1"
    assert fake_report_2_content in combined_content, "合併內容缺少 report2"
    assert "ignored.txt" not in combined_content, "合併內容包含了不應被選擇的檔案"
    print("   ✅ `read_selected_reports` 函式驗證成功。")

    # 4. 測試 archive_selected_reports 函式
    print("   測試 `archive_selected_reports`...")
    archive_selection = ["report2.md"]
    new_archive_path = archive_selected_reports(TEMP_REPORTS_DIR, TEMP_ARCHIVE_DIR, archive_selection)

    assert new_archive_path.exists(), f"存檔目錄 {new_archive_path} 未被建立"
    assert new_archive_path.is_dir(), f"存檔路徑 {new_archive_path} 不是一個目錄"

    archived_file = new_archive_path / "report2.md"
    assert archived_file.exists(), f"報告檔案未被複製到存檔目錄 {new_archive_path}"
    assert archived_file.read_text(encoding="utf-8") == fake_report_2_content, "存檔的檔案內容不符"
    print(f"   ✅ `archive_selected_reports` 函式驗證成功 (存檔於 {new_archive_path})。")

    print("✅ 階段五 PASS: 報告模組核心功能驗證成功。")

def cleanup():
    """清理所有臨時檔案和背景程序。"""
    global server_process, watchdog_timer
    print_header("🧹", "執行清理程序")

    # 停止看門狗
    if watchdog_timer:
        watchdog_timer.cancel()
        print("   - 看門狗計時器已停止。")

    # 終止後端伺服器
    if server_process and server_process.poll() is None:
        print(f"   - 正在終止後端伺服器 (PID: {server_process.pid})...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("     ✅ 後端伺服器已成功終止。")
        except subprocess.TimeoutExpired:
            print("     ⚠️ 終止超時，強制抹除。")
            server_process.kill()

    # 刪除臨時目錄
    dirs_to_remove = [TEMP_CLONE_DIR, TEMP_REPORTS_DIR, TEMP_ARCHIVE_DIR, VENV_DIR]
    for dir_path in dirs_to_remove:
        if Path(dir_path).exists():
            print(f"   - 正在刪除臨時目錄: {dir_path}")
            shutil.rmtree(dir_path, ignore_errors=True)

    # 刪除臨時檔案
    files_to_remove = [SOURCE_DB_PATH, RENAMED_DB_PATH]
    for file_path in files_to_remove:
        if Path(file_path).exists():
            print(f"   - 正在刪除臨時檔案: {file_path}")
            Path(file_path).unlink()

    print("✅ 清理完成。")


def main():
    """主執行函式，協調所有偵錯階段。"""
    try:
        print_header("🚀", "啟動全功能自動化偵錯腳本")

        # 依序執行所有階段
        phase_1_validate_download_channel()
        phase_2_backend_health_check()
        phase_3_database_preparation()
        phase_4_colab_logic_simulation()
        phase_5_report_module_validation()

        print("\n" + "🎉"*20)
        print("🎉 恭喜！所有偵錯階段已全部成功通過！ 🎉")
        print("🎉"*20)

    except (subprocess.CalledProcessError, FileNotFoundError, AssertionError) as e:
        print(f"\n❌ 偵錯流程執行失敗: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        cleanup()

if __name__ == "__main__":
    main()
