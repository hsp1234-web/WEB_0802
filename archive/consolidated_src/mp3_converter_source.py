
================================================================================
### FILE: __init__.py
================================================================================




================================================================================
### FILE: core/__init__.py
================================================================================

# -*- coding: utf-8 -*-
"""
鳳凰專案核心模組.

此檔案整合了專案的通用功能, 例如配置、日誌和資料庫管理.
透過將這些功能集中在此, 我們旨在簡化導入路徑並提高程式碼的內聚性.
"""
import logging
import logging.handlers
import multiprocessing as mp
import aiosqlite
import sys
import traceback
from pathlib import Path
from typing import Type


class BaseConfig:
    """基礎設定, 所有配置都應繼承自此類別."""

    # WebSocket 伺服器設定
    WEBSOCKET_HOST = "127.0.0.1"
    WEBSOCKET_PORT = 8000

    # 預設模型設定
    MODEL_SIZE = "tiny"
    BEAM_SIZE = 1
    LANGUAGE = None  # 自動偵測


class TestingConfig(BaseConfig):
    """
    測試配置 (Testing Profile).

    - 使用極小模型, 以利於快速啟動與驗證.
    - 適用於開發、除錯及自動化整合測試.
    """

    PROFILE_NAME = "測試模式 (Testing)"
    MODEL_SIZE = "tiny"
    BEAM_SIZE = 1


class ProductionConfig(BaseConfig):
    """
    生產配置 (Production Profile).

    - 使用效能與品質均衡的模型.
    - 適用於正式作戰部署.
    - 注意: 'medium' 模型需要較多資源, 請確保硬體規格足夠.
    """

    PROFILE_NAME = "生產模式 (Production)"
    MODEL_SIZE = "medium"
    BEAM_SIZE = 5


# --- 設定檔選擇邏輯 ---

# 建立一個 profile 名稱到設定類別的映射
_PROFILES: dict[str, Type[BaseConfig]] = {
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(profile_name: str = "testing") -> BaseConfig:
    """
    根據指定的 profile 名稱獲取對應的設定實例.

    Args:
        profile_name (str): 配置檔案的名稱 (例如 "testing", "production").
                            不區分大小寫.

    Returns:
        An instance of a config class (e.g., TestingConfig).

    Raises:
        ValueError: If the profile_name is not found.

    """
    profile_key = profile_name.lower()
    config_class = _PROFILES.get(profile_key)

    if not config_class:
        msg = f"未知的設定檔: '{profile_name}'. 可用選項: {list(_PROFILES.keys())}"
        raise ValueError(msg)

    return config_class()


# --- 常數 ---
DATABASE_FILE = "transcription_tasks.db"
UPLOAD_DIR = Path("uploads")
logger = logging.getLogger(__name__)


async def initialize_database() -> None:
    """初始化資料庫和上傳目錄, 如果資料表不存在, 則建立它."""
    try:
        # 建立上傳目錄
        UPLOAD_DIR.mkdir(exist_ok=True)

        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                """
            CREATE TABLE IF NOT EXISTS transcription_tasks (
                id TEXT PRIMARY KEY,
                original_filepath TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
                result_text TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            await db.execute(
                """
            CREATE TRIGGER IF NOT EXISTS update_transcription_tasks_updated_at
            AFTER UPDATE ON transcription_tasks
            FOR EACH ROW
            BEGIN
                UPDATE transcription_tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
            END;
            """
            )

            await db.commit()
        logger.info("資料庫 '%s' 和目錄 '%s' 已成功初始化.", DATABASE_FILE, UPLOAD_DIR)
    except aiosqlite.Error as e:
        logger.exception("資料庫初始化失敗: %s", e)
        raise


# --- 日誌系統 ---
"""
中央情報核心: 一個專業、多行程安全的日誌系統.

此模組提供了鳳凰轉錄儀後端系統所需的結構化日誌功能.
它基於 Python 的 logging 與 multiprocessing 模組, 確保來自不同作戰單位
(行程) 的日誌訊息能夠被集中、依序、且安全地寫入到單一的日誌檔案中.

作戰準則:
1.  **集中管理 (Centralized Control):** 所有日誌設定與格式化規則均在此模組中定義.
2.  **多程安全 (Process-Safe):** 使用 `multiprocessing.Queue` 作為緩衝區,
    避免多個行程同時寫入檔案導致的日誌混亂或損毀.
3.  **非阻塞寫入 (Non-Blocking):** 各個工作行程 (如 API 伺服器、轉錄工人)
    只需將日誌訊息放入佇列即可立即返回繼續執行任務, 日誌的實際 I/O 操作
    由一個專門的「書記官」行程非同步處理.
"""

# --- 常數定義 ---
LOG_FILENAME = "phoenix_transcriber.log"
LOG_FORMAT = "%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s"


def log_writer_process(log_queue: mp.Queue) -> None:
    """
    日誌書記官行程.

    這是一個獨立的行程, 其唯一職責是:
    1.  從共享的日誌佇列 (`log_queue`) 中讀取日誌記錄.
    2.  將日誌記錄寫入到指定的檔案中.

    透過這種方式, 我們將日誌的 I/O 操作與主應用程式邏輯分離,
    避免了多行程寫入同一個檔案時可能發生的競爭和鎖定問題.
    """
    # 1. 設定此行程專用的日誌處理器
    # 這個 logger 才是真正將日誌寫入檔案的執行者.
    file_handler = logging.FileHandler(LOG_FILENAME, encoding="utf-8")
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)

    # 獲取根日誌記錄器並設定
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    # 2. 進入無限迴圈, 作為一個守護行程持續運作
    while True:
        try:
            # 從佇列中獲取日誌記錄, 這是一個阻塞操作
            record = log_queue.get()

            # "毒丸" 協議: 收到 None 時, 書記官行程結束
            if record is None:
                break

            # 使用日誌記錄器來處理這條記錄
            logger = logging.getLogger(record.name)
            logger.handle(record)

        except (KeyboardInterrupt, SystemExit):
            break
        except Exception:
            # 在日誌系統本身發生錯誤時, 印出到標準錯誤流
            sys.stderr.write("--- 嚴重錯誤: 日誌書記官行程發生異常 ---\n")
            traceback.print_exc(file=sys.stderr)


from typing import Optional
def get_logger(name: str, log_queue: Optional[mp.Queue] = None) -> logging.Logger:
    """
    獲取一個配置好的日誌記錄器實例.

    這個函數是給各個子行程 (Web 伺服器、轉錄工人等) 使用的.
    它會返回一個 logger, 該 logger 不會直接將日誌寫入檔案,
    而是將日誌記錄放入一個共享的佇列中.

    Args:
        name (str): 日誌記錄器的名稱, 通常是模組名 `__name__`.
        log_queue (mp.Queue | None): 由主行程創建並傳遞過來的共享日誌佇列.

    Returns:
        logging.Logger: 一個配置好的 logger 物件.

    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重複添加 handler
    if not logger.handlers:
        if log_queue:
            # 建立一個 QueueHandler, 它會將所有通過此 logger 發出的日誌
            # 訊息 (LogRecord) 放入共享佇列中.
            queue_handler = logging.handlers.QueueHandler(log_queue)
            logger.addHandler(queue_handler)
        else:
            # 如果沒有提供佇列 (例如在單行程模式或測試中),
            # 則退回到標準的控制台輸出, 確保日誌不會丟失.
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(stream_handler)
            logger.warning("未提供日誌佇列, 日誌將輸出到控制台.")

    return logger


def get_null_logger() -> logging.Logger:
    """
    獲取一個「空」日誌記錄器.

    這個 logger 會忽略所有發送給它的訊息, 不執行任何 I/O 操作.
    這在測試情境下非常有用, 當我們不關心特定模組的日誌輸出時,
    可以傳遞這個 logger 來避免不必要的控制台雜訊或檔案寫入.

    Returns:
        logging.Logger: 一個不執行任何操作的 logger 物件.

    """
    logger = logging.getLogger("null")
    logger.addHandler(logging.NullHandler())
    logger.propagate = False  # 確保日誌事件不會被傳播到上層 logger
    return logger



================================================================================
### FILE: core/hardware.py
================================================================================

"""硬體偵測模組."""
from __future__ import annotations

from typing import Any

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def get_best_hardware_config() -> dict[str, Any]:
    """
    動態偵測硬體並返回最佳的 faster-whisper 設定.

    優先使用 CUDA, 其次是 CPU.
    如果 torch 不存在, 則直接使用 CPU.
    """
    if TORCH_AVAILABLE and torch.cuda.is_available():
        # 如果 CUDA 可用, 返回 GPU 的設定
        return {"device": "cuda", "compute_type": "float16"}
    if TORCH_AVAILABLE and torch.backends.mps.is_available():
        # Apple Silicon (MPS) 偵測
        return {"device": "mps", "compute_type": "float16"}

    # 否則, 返回 CPU 的設定
    return {"device": "cpu", "compute_type": "int8"}


if __name__ == "__main__":
    # 用於直接執行此腳本時的測試
    best_config = get_best_hardware_config()



================================================================================
### FILE: main.py
================================================================================

"""主應用程式檔案."""
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import aiofiles
import aiosqlite
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from src.core import DATABASE_FILE, UPLOAD_DIR, get_logger, initialize_database
from src.queues import add_task_to_queue

# --- Pre-emptive directory creation ---
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# --- Constants & Settings ---
logger = get_logger(__name__)


# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info("FastAPI application startup...")
    await initialize_database()
    yield
    logger.info("FastAPI application shutdown...")


# --- FastAPI App Instance ---
app = FastAPI(lifespan=lifespan)


# --- API Endpoints ---
@app.get("/health", status_code=200)
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/upload", status_code=202)
async def upload_file(
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Accept a file upload, save it, and create a new transcription task."""
    task_id = str(uuid.uuid4())
    filepath = UPLOAD_DIR / f"{task_id}_{file.filename}"

    try:
        async with aiofiles.open(filepath, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await out_file.write(content)
        logger.info("File '%s' uploaded to '%s'", file.filename, filepath)

        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                "INSERT INTO transcription_tasks (id, original_filepath) VALUES (?, ?)",
                (task_id, str(filepath)),
            )
            await db.commit()

        await add_task_to_queue(task_id)
        logger.info("Task created in database with ID: %s", task_id)

    except IOError as e:
        logger.exception("File operation failed: %s", e)
        raise HTTPException(status_code=500, detail="File operation failed.") from e
    except aiosqlite.Error as e:
        logger.exception("Database operation failed: %s", e)
        raise HTTPException(status_code=500, detail="Database operation failed.") from e

    return {"task_id": task_id}


@app.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
) -> dict[str, Any]:
    """Query and return the status and result of a task based on its ID."""
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM transcription_tasks WHERE id = ?", (task_id,)
            ) as cursor:
                task = await cursor.fetchone()

        if task is None:
            raise HTTPException(status_code=404, detail="Task ID not found")

        return dict(task)

    except aiosqlite.Error as e:
        logger.exception("Error querying task status for ID %s: %s", task_id, e)
        raise HTTPException(status_code=500, detail="Error querying status.") from e


# --- Mount Static Files ---
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    # 當直接執行此檔案時，設定一個備用的日誌系統
    if not logger.handlers or isinstance(logger.handlers[0], logging.StreamHandler):
        # 移除預設的 StreamHandler
        if logger.hasHandlers():
            logger.handlers.clear()

        # 設定一個基本的檔案日誌
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename="main_direct_run.log",
            filemode="w",
        )
        logger.info("以直接執行模式啟動, 使用 main_direct_run.log 進行日誌記錄.")

    uvicorn.run(app, host="127.0.0.1", port=8000)



================================================================================
### FILE: mock_worker.py
================================================================================

"""模擬工人模組."""
import logging
import multiprocessing as mp
import time
from typing import Any

from src.core import get_logger, get_null_logger


def process_task_from_queue(
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    logger: logging.Logger | None = None,
) -> None:
    """
    從任務佇列中獲取並處理單一任務.

    這是 `mock_worker_process` 的核心邏輯, 被提取出來以便在單體測試中直接調用.
    """
    if logger is None:
        logger = get_null_logger()  # 在沒有提供 logger 的情況下, 使用一個空 logger

    if task_queue.empty():
        logger.info("任務佇列為空, 無需處理.")
        return

    try:
        job = task_queue.get()
        if job is None:
            logger.info("收到結束信號, 任務處理終止.")
            # 將 None 放回佇列, 以防有其他消費者需要此信號
            task_queue.put(None)
            return

        job_id = job.get("job_id")
        logger.info("收到新任務: Job ID %s", job_id)

        # 模擬處理延遲
        time.sleep(0.01)  # 進一步縮短延遲以加速測試
        result_queue.put(
            {
                "status": "processing",
                "job_id": job_id,
                "progress": 50,
                "message": "模擬處理中...",
            },
        )
        logger.info("任務 %s: 正在模擬處理.", job_id)

        time.sleep(0.01)
        result = {
            "status": "completed",
            "job_id": job_id,
            "transcript": "這是一個模擬的轉錄結果.",
            "language": "zh",
            "duration": 10.0,
        }
        result_queue.put(result)
        logger.info("任務 %s: 模擬處理完成.", job_id)

    except Exception:
        logger.exception("處理任務時發生錯誤")


def mock_worker_process(
    log_queue: mp.Queue,
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    _config: dict[str, Any],
) -> None:
    """
    模擬工人行程, 用於測試.

    現在這個行程只是 `process_task_from_queue` 函數的一個循環包裝器.
    """
    logger = get_logger("模擬工人", log_queue)
    logger.info("模擬工人行程已啟動.")

    while True:
        try:
            # 檢查是否有停止信號
            if not task_queue.empty():
                job = task_queue.get()
                if job is None:
                    logger.info("收到結束信號, 模擬工人行程即將關閉.")
                    break
                # 如果不是停止信號, 把任務放回去
                task_queue.put(job)

            process_task_from_queue(task_queue, result_queue, logger)
            time.sleep(0.1)  # 避免在沒有任務時過度消耗 CPU
        except Exception:
            logger.exception("模擬工人在主循環中發生錯誤")



================================================================================
### FILE: queues.py
================================================================================

# -*- coding: utf-8 -*-
"""
基於 aiosqlite 的非同步任務佇列.

這個模組提供了一個簡單、輕量級且持久化的任務佇列.
它利用 SQLite 資料庫作為後端, 確保即使在應用程式重新啟動後,
任務也不會遺失.
"""
import asyncio
from typing import Optional

import aiosqlite

from src.core import DATABASE_FILE, get_logger

logger = get_logger(__name__)


async def add_task_to_queue(task_id: str) -> None:
    """
    將一個新任務的 ID 加入到佇列中.

    Args:
        task_id (str): 要加入佇列的任務 ID.
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                "UPDATE transcription_tasks SET status = 'pending' WHERE id = ?",
                (task_id,),
            )
            await db.commit()
            logger.info("任務 %s 已成功加入佇列.", task_id)
    except aiosqlite.Error as e:
        logger.exception("將任務 %s 加入佇列時發生資料庫錯誤: %s", task_id, e)
        raise


async def get_task_from_queue() -> Optional[str]:
    """
    從佇列中獲取一個待處理的任務.

    此函數會尋找狀態為 'pending' 的任務, 將其狀態更新為 'processing',
    然後返回其 ID. 這是原子操作, 以避免多個工人獲取同一個任務.

    Returns:
        Optional[str]: 如果找到待處理任務, 則返回任務 ID; 否則返回 None.
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            # 原子性地尋找並鎖定一個 'pending' 任務
            async with db.execute(
                "SELECT id FROM transcription_tasks WHERE status = 'pending' LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    task_id = row[0]
                    await db.execute(
                        "UPDATE transcription_tasks SET status = 'processing' WHERE id = ?",
                        (task_id,),
                    )
                    await db.commit()
                    logger.info("從佇列中領取任務 %s.", task_id)
                    return task_id
            return None
    except aiosqlite.Error as e:
        logger.exception("從佇列獲取任務時發生資料庫錯誤: %s", e)
        return None


async def update_task_status(
    task_id: str, status: str, result_text: Optional[str] = None, error_message: Optional[str] = None
) -> None:
    """
    更新任務的狀態、結果或錯誤訊息.

    Args:
        task_id (str): 要更新的任務 ID.
        status (str): 新的狀態 ('completed', 'failed', 'retry_pending').
        result_text (Optional[str]): 轉錄成功時的結果文字.
        error_message (Optional[str]): 轉錄失敗時的錯誤訊息.
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                """
                UPDATE transcription_tasks
                SET status = ?, result_text = ?, error_message = ?
                WHERE id = ?
                """,
                (status, result_text, error_message, task_id),
            )
            await db.commit()
            logger.info("任務 %s 的狀態已更新為 %s.", task_id, status)
    except aiosqlite.Error as e:
        logger.exception("更新任務 %s 狀態時發生資料庫錯誤: %s", task_id, e)
        raise



================================================================================
### FILE: transcriber_worker.py
================================================================================

"""轉錄工人模組."""
import asyncio
import multiprocessing as mp
import time
from typing import Any

from faster_whisper import WhisperModel

import aiosqlite

from src.core import DATABASE_FILE, get_logger
from src.core.hardware import get_best_hardware_config
from src.queues import get_task_from_queue, update_task_status


async def process_single_task() -> None:
    """處理單個轉錄任務."""
    logger = get_logger("轉錄工人")
    task_id = await get_task_from_queue()

    if task_id:
        logger.info("找到待處理任務: %s", task_id)

        try:
            # 執行轉錄
            hardware_config = get_best_hardware_config()
            model = WhisperModel(
                "tiny",  # Using tiny for testing
                device=hardware_config["device"],
                compute_type=hardware_config["compute_type"],
            )
            async with aiosqlite.connect(DATABASE_FILE) as db:
                async with db.execute(
                    "SELECT original_filepath FROM transcription_tasks WHERE id = ?",
                    (task_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        logger.error("在資料庫中找不到任務 %s 的檔案路徑。", task_id)
                        return
                    audio_path = row[0]
            segments, _info = model.transcribe(audio_path, beam_size=5)
            full_transcript = "".join(segment.text for segment in segments)
            logger.info("任務 %s: 轉錄完成.", task_id)

            # 更新最終結果
            await update_task_status(
                task_id, "completed", result_text=full_transcript.strip()
            )
            logger.info("任務 %s 狀態更新為: completed", task_id)

        except Exception as e:
            logger.exception("轉錄任務 %s 過程中發生錯誤", task_id)
            await update_task_status(task_id, "failed", error_message=str(e))
            logger.info("任務 %s 狀態更新為: failed", task_id)


def transcriber_worker_process(
    log_queue: mp.Queue,
    _task_queue: mp.Queue,
    _result_queue: mp.Queue,
    _config: dict[str, Any],
) -> None:
    """工人的主循環, 現在作為一個獨立的行程函數."""
    logger = get_logger("轉錄工人", log_queue)
    logger.info("真實轉錄工人行程已啟動")

    async def main() -> None:
        while True:
            try:
                await process_single_task()
                await asyncio.sleep(5)  # 每5秒檢查一次新任務
            except Exception:
                logger.exception("工人在主循環中發生嚴重錯誤")
                await asyncio.sleep(10)  # 如果發生錯誤, 等待更長時間

    asyncio.run(main())


if __name__ == "__main__":
    # 這部分保留用於獨立測試
    # 為了直接運行, 需要一個模擬的佇列
    class MockQueue:
        """模擬佇列."""

        def put(self, *args: Any, **kwargs: Any) -> None:
            """模擬 put."""
            pass

    transcriber_worker_process(MockQueue(), mp.Queue(), mp.Queue(), {})
