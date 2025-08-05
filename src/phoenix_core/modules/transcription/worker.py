# src/phoenix_core/modules/transcription/worker.py
import asyncio
import time
import traceback

from ...kernel.settings import settings
from ...kernel.hardware import get_best_hardware_config
from ...database import db_manager
from ...utils.logger import logger
from ...utils.resource_monitor import is_resource_sufficient, load_resource_settings

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
    """
    task_id = await _get_pending_task()

    if not task_id:
        return # 沒有待處理任務

    await logger.log("INFO", f"找到待處理任務: {task_id}", source="TranscriptionWorker")
    await _update_task_status(task_id, "processing")

    try:
        # 0. 資源檢查
        resource_settings = load_resource_settings()
        sufficient, message = is_resource_sufficient(resource_settings)
        if not sufficient:
            raise Exception(f"資源不足，暫停處理: {message}")

        # 1. 延遲導入 Whisper
        _lazy_import_whisper()

        # 2. 獲取硬體設定與模型
        hardware_config = get_best_hardware_config()
        model_size = settings.TRANSCRIPTION_MODEL_SIZE

        await logger.log("INFO", f"正在為任務 {task_id} 載入 Whisper 模型 '{model_size}' (設備: {hardware_config['device']}, 類型: {hardware_config['compute_type']})", source="TranscriptionWorker")
        model = WhisperModel(
            model_size,
            device=hardware_config["device"],
            compute_type=hardware_config["compute_type"],
        )

        # 3. 從資料庫獲取檔案路徑
        path_query = "SELECT original_filepath FROM transcription_tasks WHERE id = ?"
        result = await db_manager.fetch_one(path_query, (task_id,))
        if not result:
            raise FileNotFoundError(f"在資料庫中找不到任務 {task_id} 的檔案路徑。")
        audio_path = result['original_filepath']

        await logger.log("INFO", f"開始轉錄檔案: {audio_path}", source="TranscriptionWorker")

        # 4. 執行轉錄
        segments, _info = model.transcribe(audio_path, beam_size=5)
        full_transcript = "".join(segment.text for segment in segments)

        await logger.log("SUCCESS", f"任務 {task_id} 轉錄完成。", source="TranscriptionWorker")

        # 5. 更新最終結果
        await _update_task_status(task_id, "completed", message=full_transcript.strip())
        await logger.log("INFO", f"任務 {task_id} 狀態更新為: completed", source="TranscriptionWorker")

    except Exception as e:
        error_message = traceback.format_exc()
        await logger.log("ERROR", f"轉錄任務 {task_id} 過程中發生錯誤: {error_message}", source="TranscriptionWorker")
        await _update_task_status(task_id, "failed", message=error_message)
        await logger.log("INFO", f"任務 {task_id} 狀態更新為: failed", source="TranscriptionWorker")


async def transcription_worker_main_loop():
    """
    轉錄工人的主循環，定期檢查並處理新任務。
    這將被核心背景任務管理器 (`background/worker.py`) 所調用。
    """
    await logger.log("INFO", "轉錄工人背景任務已啟動，開始監聽新任務...", source="TranscriptionWorker")

    while True:
        await logger.log("DEBUG", "進入轉錄工人主循環...", source="TranscriptionWorker")
        try:
            await process_single_task()
            # 任務之間的短暫延遲，避免過度佔用 CPU 進行輪詢
            await asyncio.sleep(settings.get("TRANSCRIPTION_WORKER_POLL_INTERVAL", 5))
        except Exception as e:
            error_message = traceback.format_exc()
            await logger.log("CRITICAL", f"轉錄工人在主循環中發生無法恢復的嚴重錯誤: {e}\n{error_message}", source="TranscriptionWorker")
            # 如果發生嚴重錯誤，等待更長時間再重試
            await asyncio.sleep(60)
