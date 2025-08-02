# -*- coding: utf-8 -*-
"""
鳳凰之心日誌系統 (Phoenix Heart Logging System)

這個模組提供了專案的核心日誌功能，實現了 v82.0 報告中定義的
「真相堡壘」機制。

核心功能:
1.  **SQLite 後端**: 所有日誌都將被即時寫入一個 SQLite 資料庫 (`logs.sqlite`)，
    確保資料的持久性和完整性。
2.  **精確時間戳**: 所有日誌記錄都包含一個精確到毫秒的 ISO 8601 格式
    時間戳，並統一使用 `Asia/Taipei` 時區。
3.  **日誌分級**: 支援多種日誌等級 (INFO, SUCCESS, ERROR, etc.)。
4.  **近期日誌檢索**: 提供一個函式以供顯示模組 (DisplayManager) 高效地
    查詢最新的 N 條關鍵日誌。
5.  **日誌歸檔**: 在任務結束時，可將資料庫中的所有日誌完整地匯出為一個
    帶有時間戳的 `.txt` 純文字檔案。
"""
import sqlite3
import threading
from datetime import datetime
import pytz
import os
from typing import List, Tuple, Optional

# --- 常數定義 ---
DB_NAME = "logs.sqlite"
LOG_ARCHIVE_FOLDER = "作戰日誌歸檔"
TAIPEI_TZ = pytz.timezone("Asia/Taipei")

class Logger:
    """
    一個執行緒安全的日誌記錄器，將日誌寫入 SQLite 資料庫。
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # 實現單例模式，確保整個應用程式中只有一個 Logger 實例
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = DB_NAME):
        """
        初始化 Logger。
        Args:
            db_path: SQLite 資料庫檔案的路徑。
        """
        # 防止重複初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        self.conn.execute('PRAGMA journal_mode=WAL;') # 啟用 WAL 模式以提高並行寫入效能
        self._create_table()
        self._initialized = True

    def _get_cursor(self):
        return self.conn.cursor()

    def _create_table(self):
        """
        如果日誌表不存在，則建立它。
        """
        with self._lock:
            cursor = self._get_cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            ''')
            self.conn.commit()

    def log(self, level: str, message: str):
        """
        記錄一條新的日誌。

        Args:
            level: 日誌等級 (例如 "INFO", "ERROR")。
            message: 日誌訊息內容。
        """
        timestamp = datetime.now(TAIPEI_TZ).isoformat(timespec='milliseconds')
        with self._lock:
            cursor = self._get_cursor()
            try:
                cursor.execute(
                    "INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
                    (timestamp, level.upper(), message)
                )
                self.conn.commit()
            except sqlite3.Error as e:
                # 在無法寫入資料庫的極端情況下，至少打印到控制台
                print(f"CRITICAL: Failed to write log to database: {e}")


    def get_recent_logs(self, count: int, levels: Optional[List[str]] = None) -> List[Tuple[str, str, str]]:
        """
        從資料庫中獲取最新的 N 條日誌。

        Args:
            count: 要獲取的日誌數量。
            levels: (可選) 一個日誌等級的列表。如果提供，則只返回這些等級的日誌。

        Returns:
            一個元組列表，每個元組包含 (timestamp, level, message)。
        """
        with self._lock:
            cursor = self._get_cursor()
            if levels:
                # 建立參數化查詢的問號字串
                placeholders = ','.join('?' for _ in levels)
                query = f"""
                    SELECT timestamp, level, message FROM logs
                    WHERE level IN ({placeholders})
                    ORDER BY id DESC
                    LIMIT ?
                """
                params = levels + [count]
            else:
                query = """
                    SELECT timestamp, level, message FROM logs
                    ORDER BY id DESC
                    LIMIT ?
                """
                params = (count,)

            try:
                cursor.execute(query, params)
                # 結果是 DESC 排序，我們需要反轉它以獲得正確的時間順序
                return list(reversed(cursor.fetchall()))
            except sqlite3.Error as e:
                print(f"ERROR: Failed to fetch recent logs: {e}")
                return []

    def archive_logs_to_file(self) -> Optional[str]:
        """
        將資料庫中的所有日誌歸檔到一個文字檔案中。

        Returns:
            歸檔檔案的路徑，如果失敗則返回 None。
        """
        if not os.path.exists(LOG_ARCHIVE_FOLDER):
            os.makedirs(LOG_ARCHIVE_FOLDER)

        start_time_str = datetime.now(TAIPEI_TZ).strftime("%Y%m%d_%H%M%S_%f")[:-3]
        archive_filename = f"log_archive_{start_time_str}.txt"
        archive_filepath = os.path.join(LOG_ARCHIVE_FOLDER, archive_filename)

        with self._lock:
            cursor = self._get_cursor()
            try:
                cursor.execute("SELECT timestamp, level, message FROM logs ORDER BY id ASC")
                all_logs = cursor.fetchall()

                with open(archive_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"--- 鳳凰之心作戰日誌歸檔 ---\n")
                    f.write(f"歸檔時間: {datetime.now(TAIPEI_TZ).isoformat()}\n")
                    f.write(f"總日誌數: {len(all_logs)}\n")
                    f.write("="*40 + "\n\n")

                    for timestamp, level, message in all_logs:
                        f.write(f"[{timestamp}] [{level}] {message}\n")

                return archive_filepath
            except (sqlite3.Error, IOError) as e:
                print(f"ERROR: Failed to archive logs to file: {e}")
                return None

    def close(self):
        """
        關閉資料庫連線。
        """
        if self.conn:
            self.conn.close()

# 建立一個全域的 Logger 實例，方便其他模組直接匯入使用
# from .logger import logger
logger = Logger()
