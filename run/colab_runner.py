# -*- coding: utf-8 -*-
import sqlite3
import time
import sys
from datetime import datetime, timezone
import requests

# --- 設定 ---
DB_PATH = "state.db"
HEALTH_CHECK_URL = "http://127.0.0.1:8088/monitor/health"
HEARTBEAT_KEY = "system_heartbeat"
HEARTBEAT_TABLE = "status_updates"
WATCHDOG_SECONDS = 15
LOOP_SLEEP_SECONDS = 5

def print_log(message):
    """Prints a message with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_backend_health():
    """
    主動健康檢查：探測後端健康檢查 API 端點。
    """
    try:
        response = requests.get(HEALTH_CHECK_URL, timeout=3)
        if response.status_code == 200:
            print_log(f"✅ 健康檢查成功: 後端 API 在 {HEALTH_CHECK_URL} 回應正常。")
            return True
        else:
            print_log(f"⚠️ 健康檢查警告: 後端 API 回應狀態碼 {response.status_code}。")
            return False
    except requests.exceptions.RequestException as e:
        print_log(f"❌ 健康檢查失敗: 無法連接到後端 API ({e})。")
        return False

def check_database_heartbeat(conn):
    """
    心跳檢查：讀取 status_updates 表中的 system_heartbeat 時間戳。
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT timestamp FROM {HEARTBEAT_TABLE} WHERE key = ?", (HEARTBEAT_KEY,)
        )
        result = cursor.fetchone()

        if result is None:
            print_log(f"⚠️ 心跳檢查警告: 在 '{HEARTBEAT_TABLE}' 中找不到 '{HEARTBEAT_KEY}' 的紀錄。")
            return False

        last_heartbeat_str = result[0]
        try:
            if 'Z' in last_heartbeat_str or '+' in last_heartbeat_str:
                 last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
            else:
                 last_heartbeat = datetime.fromisoformat(last_heartbeat_str).replace(tzinfo=timezone.utc)
        except ValueError:
            last_heartbeat = datetime.strptime(last_heartbeat_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        time_diff = (now_utc - last_heartbeat).total_seconds()

        print_log(f"💓 心跳檢查: 最後心跳時間戳為 {last_heartbeat_str} (延遲 {time_diff:.2f} 秒)。")

        if time_diff > WATCHDOG_SECONDS:
            print_log(f"🚨🚨🚨 看門狗錯誤：後端心跳已停止超過 {WATCHDOG_SECONDS} 秒！")
            return False

        return True

    except sqlite3.Error as e:
        print_log(f"❌ 資料庫錯誤: 查詢心跳時發生錯誤: {e}")
        return False

def read_and_print_data(conn):
    """
    如果心跳正常，則查詢其他三張表並打印原始數據。
    """
    tables_to_read = ["logs", "hardware_stats", "status_updates"]
    try:
        cursor = conn.cursor()
        for table in tables_to_read:
            print_log(f"--- 正在讀取 '{table}' 表的最新 3 筆資料 ---")
            order_col = ''
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            if 'timestamp' in columns:
                order_col = 'timestamp'
            elif 'id' in columns:
                order_col = 'id'

            query = f"SELECT * FROM {table}"
            if order_col:
                query += f" ORDER BY {order_col} DESC"
            query += " LIMIT 3"

            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                print_log(f"   (無資料)")
            for row in rows:
                print_log(f"   {row}")
    except sqlite3.Error as e:
        print_log(f"❌ 資料庫錯誤: 讀取資料時發生錯誤: {e}")

def main():
    """
    主執行迴圈。
    此版本為安全重構的最終版本，包含了經過驗證的看門狗監控邏輯。
    """
    print_log("🚀 Colab Runner (安全模式) 已啟動。")

    while True:
        # 1. 主動健康檢查
        if not check_backend_health():
            print_log("🛑 後端 API 無法訪問，Runner 退出。")
            sys.exit(1)

        conn = None
        try:
            # 2. 連接資料庫
            conn = sqlite3.connect(DB_PATH)

            # 3. 心跳檢查 (看門狗)
            if not check_database_heartbeat(conn):
                print_log("🛑 心跳檢查失敗，Runner 退出。")
                sys.exit(1)

            # 4. 數據讀取
            print_log("✅ 心跳正常，繼續讀取資料...")
            read_and_print_data(conn)

        except sqlite3.Error as e:
            print_log(f"❌ 發生嚴重的資料庫連接錯誤: {e}")
            sys.exit(1)
        finally:
            if conn:
                conn.close()

        # 5. 等待下一次循環
        print_log(f"--- 等待 {LOOP_SLEEP_SECONDS} 秒後進行下一次檢查 ---")
        time.sleep(LOOP_SLEEP_SECONDS)

if __name__ == "__main__":
    main()
