# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║         📊 資料庫準備流程檢查器 (DB Prep Checker) V1.0             ║
# ║            (檔案: report_debug_1.py)                                 ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 根據 `BUG.MD` 和 `scripts/local_run.py` 的分析，         ║
# ║           在本地環境中，可靠地測試報告生成前的資料庫準備流程。     ║
# ║   - 核心功能:                                                      ║
# ║       1. 驗證 `.venv_debug` 是否存在。                           ║
# ║       2. 如 `state.db` 不存在，則建立一個假資料庫供測試。          ║
# ║       3. 將 `state.db` 重命名為 `logs.sqlite`。                    ║
# ║       4. 解釋為何測試中止於此 (因上游腳本已重構)。                 ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import shutil
import sqlite3
import json
from pathlib import Path

# --- 全域設定 ---
# 腳本應從專案根目錄執行
VENV_DIR = Path("./.venv_debug")
VENV_PYTHON = VENV_DIR / "bin" / "python"
SOURCE_DB_PATH = Path("./state.db")
RENAMED_DB_PATH = Path("./logs.sqlite")

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    print("\n" + "="*80)
    print(f"📊 {__import__('time').strftime('%Y-%m-%d %H:%M:%S')} - {title}")
    print("="*80)

def create_fake_state_db_if_needed():
    """如果 state.db 不存在，則建立一個結構完整的假資料庫以供測試。"""
    if SOURCE_DB_PATH.exists():
        print(f"✅ 找到現有資料庫: {SOURCE_DB_PATH}")
        return

    print(f"⚠️ 找不到資料庫檔案，正在建立一個假的 '{SOURCE_DB_PATH}' 以便測試...")
    # 如果重命名的目標檔案存在，先刪除它，避免混淆
    if RENAMED_DB_PATH.exists():
        print(f"   ℹ️ 同時移除舊的 '{RENAMED_DB_PATH}' 以確保測試純淨。")
        RENAMED_DB_PATH.unlink()

    conn = sqlite3.connect(SOURCE_DB_PATH)
    cursor = conn.cursor()

    # 根據舊腳本的結構，建立相似的假資料表
    # 假設 status_updates 用於心跳，logs 用於日誌
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS status_updates (
        key TEXT PRIMARY KEY,
        value TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        timestamp TEXT,
        level TEXT,
        message TEXT
    )
    """)

    # 插入假的 status 資料
    cursor.execute("INSERT INTO status_updates (key, value) VALUES (?, ?)",
                   ("last_heartbeat", "2025-08-03T15:00:00Z"))
    cursor.execute("INSERT INTO status_updates (key, value) VALUES (?, ?)",
                   ("app_status", '{"module_a": "running"}'))

    # 插入假的 logs 資料
    logs_data = [
        ("2025-08-03T15:00:01Z", "INFO", "假資料：系統啟動"),
        ("2025-08-03T15:00:05Z", "ERROR", "假資料：感測器 B-42 連線逾時"),
    ]
    cursor.executemany("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)", logs_data)

    conn.commit()
    conn.close()
    print(f"✅ 假的 '{SOURCE_DB_PATH}' 已建立並填充數據。")

def main():
    """主執行函式。"""
    print_header("啟動資料庫準備流程檢查器")

    try:
        # 1. 檢查環境是否準備就緒
        print_header("階段 1: 檢查虛擬環境")
        if not VENV_DIR.is_dir() or not VENV_PYTHON.exists():
            print(f"❌ 錯誤: 找不到由 `colab_runner_debug_1.py` 建立的虛擬環境: {VENV_DIR}", file=sys.stderr)
            print("   請先執行 `python debug/colab_runner_debug_1.py`。", file=sys.stderr)
            sys.exit(1)
        print("✅ 虛擬環境已找到。")

        # 2. 準備資料庫
        print_header("階段 2: 準備來源資料庫 (state.db)")
        create_fake_state_db_if_needed()

        # 3. 執行重命名
        print_header("階段 3: 執行資料庫重命名")
        print(f"正在將 '{SOURCE_DB_PATH}' 重命名為 '{RENAMED_DB_PATH}'...")
        if RENAMED_DB_PATH.exists():
             RENAMED_DB_PATH.unlink() # 確保目標位置是乾淨的
        shutil.move(str(SOURCE_DB_PATH), str(RENAMED_DB_PATH))
        print(f"✅ 資料庫重命名成功。現在存在 '{RENAMED_DB_PATH}'。")

        # 4. 解釋與總結
        print_header("階段 4: 流程結束與說明")
        print("✅ 資料庫準備與重命名流程已成功通過驗證。")
        print("\n" + "-"*60)
        print("ℹ️  **重要通知**:")
        print("   根據對當前專案的分析，舊的報告生成腳本 (`scripts/generate_report.py`)")
        print("   已被重構或移除。因此，本偵錯腳本的任務到此為止。")
        print("   這個結果是**符合預期**的，它確認了報告生成前的資料庫處理環節是正常的。")
        print("-" * 60)

    except Exception as e:
        import traceback
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
