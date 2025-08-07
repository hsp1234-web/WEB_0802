# src/phoenix_core/modules/transcription/worker.py
import asyncio
import gc
import os
import sys
import traceback

# 導入 torch 是為了檢查 CUDA
# import torch # 暫時禁用，以測試是否是 torch 本身導致崩潰

from ...kernel.settings import settings
from ...database import db_manager
from ...utils.logger import logger

# 延遲導入，以避免循環依賴
WhisperModel = None

def _lazy_import_whisper():
    """延遲導入 faster_whisper，僅在實際需要時才執行。"""
    global WhisperModel
    if WhisperModel is None:
        try:
            from faster_whisper import WhisperModel as WhisperModel_
            WhisperModel = WhisperModel_
        except ImportError:
            raise ImportError("Could not import faster_whisper. Please ensure it is installed.")

async def _get_pending_task():
    """從資料庫獲取一個待處理的任務。"""
    query = "SELECT id FROM transcription_tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
    task = await db_manager.fetch_one(query)
    return task['id'] if task else None

async def _update_task_status(task_id, status, message=None):
    """更新資料庫中任務的狀態。"""
    if status == "completed":
        query = "UPDATE transcription_tasks SET status = ?, result_text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        await db_manager.execute_query(query, (status, message, task_id))
    elif status == "failed":
        query = "UPDATE transcription_tasks SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        await db_manager.execute_query(query, (status, message, task_id))
    else: # processing
        query = "UPDATE transcription_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        await db_manager.execute_query(query, (status, task_id))


async def process_single_task():
    """
    完整處理一個轉錄任務的流程：領取、處理、更新結果。
    *** 終極簡化模式：強制純 CPU ***
    """
    task_id = await _get_pending_task()
    if not task_id:
        return

    await logger.log("INFO", f"找到待處理任務: {task_id}", source="TranscriptionWorker")
    await _update_task_status(task_id, "processing")

    model = None
    try:
        # 1. 延遲導入 Whisper
        _lazy_import_whisper()

        # 2. 強制使用最基礎的純 CPU 模式
        device = "cpu"
        compute_type = "int8"
        model_size = settings.TRANSCRIPTION_MODEL_SIZE

        await logger.log("INFO", f"正在為任務 {task_id} 載入 Whisper 模型 '{model_size}' (終極強制 CPU 模式)", source="TranscriptionWorker")
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

        # 3. 從資料庫獲取檔案路徑
        path_query = "SELECT original_filepath FROM transcription_tasks WHERE id = ?"
        result = await db_manager.fetch_one(path_query, (task_id,))
        if not result:
            raise FileNotFoundError(f"在資料庫中找不到任務 {task_id} 的檔案路徑。")
        audio_path = result['original_filepath']

        # 4. 執行轉錄
        loop = asyncio.get_running_loop()
        segments, _info = await loop.run_in_executor(
            None,
            lambda: model.transcribe(audio_path, beam_size=5)
        )

        full_transcript = "".join(segment.text.strip() for segment in segments)

        await logger.log("SUCCESS", f"任務 {task_id} 轉錄完成。", source="TranscriptionWorker")

        # 5. 更新最終結果
        await _update_task_status(task_id, "completed", message=full_transcript)

    except Exception as e:
        error_message = traceback.format_exc()
        await logger.log("ERROR", f"轉錄任務 {task_id} 過程中發生錯誤: {error_message}", source="TranscriptionWorker")
        await _update_task_status(task_id, "failed", message=error_message)

    finally:
        if model is not None:
            del model
            gc.collect()


async def transcription_worker_main_loop():
    """
    轉錄工人的主循環，定期檢查並處理新任務。
    """
    await logger.log("INFO", "轉錄工人背景任務已啟動 (終極強制 CPU 模式)，開始監聽新任務...", source="TranscriptionWorker")

    while True:
        try:
            await process_single_task()
            await asyncio.sleep(settings.get("TRANSCRIPTION_WORKER_POLL_INTERVAL", 5))
        except Exception as e:
            error_message = traceback.format_exc()
            await logger.log("CRITICAL", f"轉錄工人在主循環中發生無法恢復的嚴重錯誤: {e}\n{error_message}", source="TranscriptionWorker")
            await asyncio.sleep(60)
