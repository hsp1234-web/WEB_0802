# -*- coding: utf-8 -*-
"""
鳳凰之心日誌系統 (Phoenix Heart Logging System)

V2 架構:
此模組現在是一個輕量級的日誌記錄「代理」。
它唯一的職責是將日誌請求轉發給核心的 DatabaseManager，
不再處理任何直接的檔案 I/O 或資料庫連接。
這確保了所有日誌都流經同一個「真相來源」(state.db)。
"""
import threading
import asyncio
import sys
from ..database import db_manager
from typing import List, Tuple, Optional

class Logger:
    """
    一個執行緒安全的日誌記錄代理，將日誌記錄任務委派給 DatabaseManager。
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

    def __init__(self):
        """
        初始化 Logger。此版本中無需進行任何 I/O 初始化。
        """
        pass

    async def log(self, level: str, message: str, source: Optional[str] = "default"):
        """
        以非同步方式記錄一條新的日誌。
        此方法會將同步的資料庫寫入操作放在背景執行緒中執行，以避免阻塞事件循環。

        Args:
            level (str): 日誌等級 (例如 "INFO", "ERROR")。
            message (str): 日誌訊息內容。
            source (str, optional): 日誌來源。預設為 "default"。
        """
        try:
            # 【V68 除錯修改】同時打印到 stdout，以便 safe_runner.py 的看門狗可以監控到活動。
            # 在生產環境中，可以考慮移除此 print 或透過設定來控制。
            print(f"[{level.upper()}] [{source}] {message}", file=sys.stdout, flush=True)

            # 在背景執行緒中執行同步的資料庫寫入操作
            await asyncio.to_thread(
                db_manager.write_log,
                level=level.upper(),
                message=message,
                source=source
            )
        except Exception as e:
            # 在極端情況下，如果連 db_manager 都失敗了，打印到 stderr
            # 這是一個應急措施，正常情況下不應發生
            print(f"CRITICAL LOGGER FAILURE: Could not delegate log to DatabaseManager: {e}")

# 建立一個全域的 Logger 實例，方便其他模組直接匯入使用
# from .logger import logger
logger = Logger()
