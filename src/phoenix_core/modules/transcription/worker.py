# src/phoenix_core/modules/transcription/worker.py
import asyncio
import gc
import os
import sys
import traceback

# src/phoenix_core/modules/transcription/worker.py
import asyncio
import gc
import traceback
from pathlib import Path

from ...kernel.settings import settings
from ...database import db_manager
from ...utils.logger import logger

# 延遲導入，以避免循環依賴
Whisper = None

def _lazy_import_whisper():
    """延遲導入 whisper_cpp，僅在實際需要時才執行。"""
    global Whisper
    if Whisper is None:
        try:
            # 感謝使用者建議，我們改用 whisper-cpp-python，它更輕量且專為 CPU 優化
            from whisper_cpp import Whisper
        except ImportError:
            raise ImportError("Could not import whisper_cpp. Please ensure whisper-cpp-python is installed.")

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
    使用 whisper-cpp-python 進行純 CPU 轉錄。
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

        # 2. 準備模型
        model_size = settings.TRANSCRIPTION_MODEL_SIZE
        # whisper-cpp-python 會自動下載模型到快取目錄
        # 我們只需要指定模型名稱
        await logger.log("INFO", f"正在為任務 {task_id} 準備 Whisper.cpp 模型 '{model_size}' (純 CPU)", source="TranscriptionWorker")
        model = Whisper(model_name=model_size)

        # 3. 從資料庫獲取檔案路徑
        path_query = "SELECT original_filepath FROM transcription_tasks WHERE id = ?"
        result = await db_manager.fetch_one(path_query, (task_id,))
        if not result:
            raise FileNotFoundError(f"在資料庫中找不到任務 {task_id} 的檔案路徑。")
        audio_path = Path(result['original_filepath'])

        if not audio_path.exists():
            raise FileNotFoundError(f"任務 {task_id} 的音訊檔案不存在於: {audio_path}")

        # 4. 執行轉錄
        # whisper-cpp-python 的 transcribe 是 CPU 密集型操作，需在 executor 中運行
        loop = asyncio.get_running_loop()

        # 將音訊檔案讀入記憶體中傳遞，以獲得更好的相容性
        audio_bytes = await loop.run_in_executor(None, audio_path.read_bytes)

        transcript_data = await loop.run_in_executor(
            None,
            model.transcribe,
            audio_bytes
        )

        full_transcript = transcript_data.get("text", "").strip()

        await logger.log("SUCCESS", f"任務 {task_id} 轉錄完成。", source="TranscriptionWorker")

        # 5. 更新最終結果
        await _update_task_status(task_id, "completed", message=full_transcript)

    except Exception as e:
        error_message = traceback.format_exc()
        await logger.log("ERROR", f"轉錄任務 {task_id} 過程中發生錯誤: {error_message}", source="TranscriptionWorker")
        await _update_task_status(task_id, "failed", message=error_message)

    finally:
        # whisper-cpp-python 的模型由 C++ 管理，Python 這邊不需手動 del
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
