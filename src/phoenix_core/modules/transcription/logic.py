# src/phoenix_core/modules/transcription/logic.py
import uuid
from pathlib import Path
from fastapi import UploadFile
import aiofiles

from ...kernel.settings import settings
from ...database import db_manager
from ...utils.logger import logger

# 根據 settings 來決定上傳目錄
UPLOAD_DIR = Path(settings.APP_STORAGE) / "transcription_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def create_transcription_task(file: UploadFile) -> str:
    """
    創建一個新的轉錄任務，包括儲存檔案和在資料庫中建立紀錄。

    Args:
        file: 從 API 端點傳入的 UploadFile 物件。

    Returns:
        新建立任務的 task_id。
    """
    await logger.log("INFO", f"接收到新的檔案上傳請求: {file.filename}", source="TranscriptionAPI")

    task_id = str(uuid.uuid4())
    # Sanitize the filename to prevent security issues like directory traversal
    sanitized_filename = Path(file.filename).name
    filepath = UPLOAD_DIR / f"{task_id}_{sanitized_filename}"

    try:
        # 非同步寫入檔案
        async with aiofiles.open(filepath, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)

        # 在資料庫中創建任務紀錄 (這裡假設 db_manager 有一個異步方法)
        # 注意：我們將在這裡使用一個假定存在的 `create_task` 方法
        # 實際的資料庫操作將在 `db_queries.py` 或類似檔案中實現
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        await db_manager.execute_query(
            "INSERT INTO transcription_tasks (id, original_filepath, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, str(filepath), "pending", now, now)
        )

        # TODO: 將 task_id 推送到背景工作佇列
        # from ..background.worker import task_queue
        # await task_queue.put(task_id)

    except Exception as e:
        # 在實際應用中，這裡應該有更完善的錯誤處理和日誌記錄
        print(f"Error creating task: {e}")
        raise

    return task_id

async def get_task_status_by_id(task_id: str) -> dict | None:
    """
    根據任務 ID 從資料庫中查詢任務狀態。

    Args:
        task_id: 要查詢的任務 ID。

    Returns:
        一個包含任務狀態的字典，如果找不到則返回 None。
    """
    # 這裡同樣使用一個假定存在的查詢方法
    result = await db_manager.fetch_one(
        "SELECT id, status, result_text, error_message, created_at, updated_at FROM transcription_tasks WHERE id = ?",
        (task_id,)
    )

    return result
