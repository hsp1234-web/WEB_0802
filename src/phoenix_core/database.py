# -*- coding: utf-8 -*-
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
import pytz
from .kernel.settings import settings

class DatabaseManager:
    """
    一個集中管理 SQLite 資料庫連接的類別，為多執行緒環境設計。
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
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.db_path = Path(db_path)
        self.thread_local = threading.local()
        self._initialized = True
        self._initialize_database()

    def _initialize_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS hardware_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                gpu_temperature REAL
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS status_updates (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """)
            conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(self.thread_local, "connection"):
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.execute("PRAGMA journal_mode=WAL;")
                self.thread_local.connection = conn
            except sqlite3.Error as e:
                print(f"資料庫連接失敗: {e}")
                raise
        return self.thread_local.connection

    def close_connection(self):
        if hasattr(self.thread_local, "connection"):
            self.thread_local.connection.close()
            del self.thread_local.connection

    def write_log(self, level: str, message: str, source: str = "backend"):
        if getattr(settings.LOG_SETTINGS, level.upper(), True):
            timestamp = datetime.now(pytz.utc).isoformat()
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO logs (timestamp, level, message, source) VALUES (?, ?, ?, ?)",
                    (timestamp, level, message, source)
                )
                conn.commit()

    def write_hardware_stat(self, cpu_usage: float, memory_usage: float, disk_usage: float, gpu_temperature: float):
        timestamp = datetime.now(pytz.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO hardware_stats (timestamp, cpu_usage, memory_usage, disk_usage, gpu_temperature) VALUES (?, ?, ?, ?, ?)",
                (timestamp, cpu_usage, memory_usage, disk_usage, gpu_temperature)
            )
            conn.commit()

    def write_status_update(self, key: str, value: str):
        timestamp = datetime.now(pytz.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO status_updates (key, value, timestamp) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, timestamp=excluded.timestamp",
                (key, value, timestamp)
            )
            conn.commit()

    def get_status(self, key: str) -> str | None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM status_updates WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_logs_since(self, timestamp: datetime) -> list[dict]:
        timestamp_str = timestamp.isoformat()
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, level, message FROM logs WHERE timestamp > ? ORDER BY timestamp ASC",
                (timestamp_str,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

db_manager = DatabaseManager()
