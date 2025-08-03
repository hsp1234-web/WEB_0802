# -*- coding: utf-8 -*-
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
import pytz

class DatabaseManager:
    """
    一個集中管理 SQLite 資料庫連接的類別，為多執行緒環境設計。

    核心特性：
    - **執行緒安全**: 使用 `threading.local()` 為每個執行緒提供獨立的資料庫連接，
      避免了在執行緒間共享連接所導致的不可預期錯誤。
    - **WAL 模式**: 在首次建立連接時，自動啟用 Write-Ahead Logging (WAL) 模式，
      顯著提升高併發讀寫的效能與穩定性。
    - **單例模式 (Singleton-like)**: 整個應用程式應共享同一個 DatabaseManager 實例，
      以確保所有操作都指向同一個資料庫檔案和設定。
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "state.db"):
        # 防止重複初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.db_path = Path(db_path)
        self.thread_local = threading.local()
        self._initialized = True
        self._initialize_database()

    def _initialize_database(self):
        """
        初始化資料庫檔案，建立必要的表格。
        這個方法只在主執行緒中被呼叫一次。
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 建立日誌表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT
            )
            """)
            # 建立狀態表 (鍵值對儲存)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS status (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """)
            conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        """
        為當前執行緒獲取一個資料庫連接。
        如果連接不存在，則建立一個新的連接，並設定為 WAL 模式。
        """
        if not hasattr(self.thread_local, "connection"):
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                # 啟用 WAL 模式以實現高併發讀寫
                conn.execute("PRAGMA journal_mode=WAL;")
                self.thread_local.connection = conn
            except sqlite3.Error as e:
                print(f"資料庫連接失敗: {e}")
                raise
        return self.thread_local.connection

    def close_connection(self):
        """關閉當前執行緒的資料庫連接。"""
        if hasattr(self.thread_local, "connection"):
            self.thread_local.connection.close()
            del self.thread_local.connection

    def log(self, level: str, message: str, source: str = "backend"):
        """
        寫入一條日誌到 logs 表。
        """
        timestamp = datetime.now(pytz.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO logs (timestamp, level, message, source) VALUES (?, ?, ?, ?)",
                (timestamp, level, message, source)
            )
            conn.commit()

    def set_status(self, key: str, value: str):
        """
        設定一個狀態值到 status 表 (UPSERT 邏輯)。
        """
        timestamp = datetime.now(pytz.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO status (key, value, timestamp) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, timestamp=excluded.timestamp
                """,
                (key, value, timestamp)
            )
            conn.commit()

    def get_status(self, key: str) -> str | None:
        """
        從 status 表讀取一個狀態值。
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM status WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None

# 為了方便在應用程式中共享，匯出一個預設實例
# 在應用程式的不同模組中，可以透過 `from .database import db_manager` 來取得同一個實例
db_manager = DatabaseManager()
