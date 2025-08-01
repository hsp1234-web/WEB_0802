# 檔案: scripts/launch.py
# 說明: 專案的核心後端服務，負責執行任務並透過資料庫更新狀態。

import sqlite3
import time
import subprocess
import sys
import os
from pathlib import Path
import logging

DB_PATH = Path("state.db")
LOG_PATH = Path("uvicorn.log")

# --- 設定日誌 ---
# 我們將日誌同時輸出到檔案和控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- 資料庫管理 ---
def setup_database(db_path):
    """建立資料庫和 status 表格。"""
    logging.info(f"正在設定資料庫於: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS status (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    logging.info("資料庫表格 'status' 已確認存在。")
    return conn

def update_status(conn, key, value):
    """使用傳入的連線更新狀態。"""
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO status (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        logging.info(f"狀態更新: {key} = {value}")
    except Exception as e:
        logging.error(f"更新狀態時發生錯誤: {e}")

# --- 核心業務邏輯 ---
def core_logic(conn):
    """模擬專案的核心業務邏輯。"""
    logging.info("核心任務：啟動中...")
    update_status(conn, "current_status", "核心任務：啟動中...")
    time.sleep(2) # 縮短時間以利測試

    logging.info("核心任務：正在處理數據...")
    update_status(conn, "current_status", "核心任務：正在處理數據...")
    time.sleep(3)

    logging.info("核心任務：處理完畢。")
    update_status(conn, "current_status", "核心任務：處理完畢。")

# --- 主執行函數 ---
def main():
    """主執行函數，協調所有操作。"""
    # 清理舊檔案
    if DB_PATH.exists():
        os.remove(DB_PATH)
    if LOG_PATH.exists():
        os.remove(LOG_PATH)

    conn = None
    try:
        conn = setup_database(DB_PATH)
        update_status(conn, "current_status", "後端服務已啟動")

        core_logic(conn)

        update_status(conn, "current_status", "任務成功完成")
        logging.info("所有核心任務成功完成。")

    except Exception as e:
        logging.error(f"執行 main 函式時發生未預期的錯誤: {e}")
        if conn:
            update_status(conn, "current_status", f"任務失敗: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("資料庫連線已關閉。")

        # --- 任務結束後，呼叫報告生成器 ---
        logging.info("準備生成最終報告...")
        try:
            result = subprocess.run(
                [sys.executable, "scripts/report_generator.py", "--report", "all"],
                check=True, capture_output=True, text=True, encoding='utf-8'
            )
            logging.info("報告生成成功。")
            # logging.info(f"報告生成器輸出:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            logging.error(f"報告生成腳本執行失敗: {e.stderr}")

        logging.info("launch.py 執行完畢。")

if __name__ == "__main__":
    main()
