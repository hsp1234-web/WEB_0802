# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              📊 本地報告生成偵錯執行器 V1.0                          ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 在本地環境中，可靠地測試報告生成流程。                   ║
# ║   - 假設: 此腳本應在 `colab_runner_debug.py` 執行完畢後運行，       ║
# ║           它會使用由前者建立的 `.venv_debug` 虛擬環境。              ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
import sqlite3
from pathlib import Path

# --- 全域設定 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv_debug"
VENV_PYTHON = VENV_DIR / "bin" / "python"
DB_PATH = PROJECT_ROOT / "logs.sqlite"
REPORT_SCRIPT = PROJECT_ROOT / "scripts" / "generate_report.py"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements" / "report.txt"
REPORT_DIR = PROJECT_ROOT / "reports"

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    print("\n" + "="*80)
    print(f"📊 {__import__('time').strftime('%Y-%m-%d %H:%M:%S')} - {title}")
    print("="*80)

def run_command(command, cwd=".", check=True):
    """執行一個子程序命令並打印其輸出。"""
    print(f"   🔹 執行命令: {' '.join(map(str, command))}")
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, encoding='utf-8',
            cwd=str(cwd), check=check
        )
        if result.stdout:
            print(f"     [STDOUT] {result.stdout.strip()}")
        if result.stderr:
            print(f"     [STDERR] {result.stderr.strip()}", file=sys.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        if e.stdout: print(f"   [失敗的 STDOUT]:\n{e.stdout}", file=sys.stderr)
        if e.stderr: print(f"   [失敗的 STDERR]:\n{e.stderr}", file=sys.stderr)
        raise

import json

def create_fake_database_if_needed():
    """如果資料庫檔案不存在，則建立一個結構完整的假資料庫以供測試。"""
    if DB_PATH.exists():
        print(f"✅ 找到現有資料庫: {DB_PATH}")
        return

    print(f"⚠️ 找不到資料庫檔案，正在建立一個假的 '{DB_PATH}' 以便測試...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 建立 status 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS status (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # 建立 logs 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        timestamp TEXT,
        level TEXT,
        message TEXT
    )
    """)

    # 插入假的 status 資料
    apps_status = {
        "dataprovider": "running",
        "system_monitor": "stopped",
    }
    cursor.execute("INSERT INTO status (key, value) VALUES (?, ?)",
                   ("final_stage", "假資料：任務完成"))
    cursor.execute("INSERT INTO status (key, value) VALUES (?, ?)",
                   ("final_apps_status", json.dumps(apps_status)))

    # 插入假的 logs 資料
    logs_data = [
        ("2025-08-01T12:00:00Z", "INFO", "假資料：系統啟動"),
        ("2025-08-01T12:05:00Z", "ERROR", "假資料：AI 模組載入失敗"),
    ]
    cursor.executemany("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)", logs_data)

    conn.commit()
    conn.close()
    print(f"✅ 假的資料庫已建立並填充數據。")


def main():
    """主執行函式。"""
    print_header("啟動本地報告生成偵錯執行器")

    try:
        # 1. 檢查環境是否準備就緒
        print_header("階段 1: 檢查環境")
        if not VENV_DIR.is_dir() or not VENV_PYTHON.exists():
            print(f"❌ 錯誤: 找不到由 `colab_runner_debug.py` 建立的虛擬環境: {VENV_DIR}", file=sys.stderr)
            print("   請先執行 `python run/colab_runner_debug.py`。", file=sys.stderr)
            sys.exit(1)
        print("✅ 虛擬環境已找到。")

        create_fake_database_if_needed()

        if not REPORT_SCRIPT.exists():
            print(f"❌ 錯誤: 找不到報告生成腳本: {REPORT_SCRIPT}", file=sys.stderr)
            sys.exit(1)
        print("✅ 報告生成腳本已找到。")

        # 2. 安裝報告專用依賴
        print_header("階段 2: 安裝報告依賴")
        if REQUIREMENTS_FILE.exists():
            run_command([
                str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)
            ])
            print("✅ 報告依賴安裝完成。")
        else:
            print(f"⚠️  警告: 找不到報告依賴檔案 '{REQUIREMENTS_FILE}'，跳過安裝。")

        # 3. 執行報告生成腳本
        print_header("階段 3: 執行報告生成")
        REPORT_DIR.mkdir(exist_ok=True) # 確保報告目錄存在
        run_command([
            str(VENV_PYTHON), str(REPORT_SCRIPT),
            "--db-file", str(DB_PATH),
            "--report-dir", str(REPORT_DIR)
        ])
        print("✅ 報告生成流程執行完畢。")
        print(f"   請查看 '{REPORT_DIR}' 目錄下的報告。")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n❌ 偵錯流程執行失敗: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
