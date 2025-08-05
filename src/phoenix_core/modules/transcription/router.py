# src/phoenix_core/modules/transcription/router.py
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import Any

from ...kernel.registry import register_router
from . import logic

# 建立一個新的 API 路由器
router = APIRouter(
    prefix="/transcription",
    tags=["音訊轉錄 (Transcription)"],
)

@router.post("/upload", status_code=202, summary="上傳音訊檔案並開始轉錄")
async def upload_file(
    file: UploadFile = File(...),
) -> dict[str, str]:
    """
    接收音訊檔案上傳，將其儲存，並建立一個新的轉錄任務。

    - **file**: 必要參數，上傳的音訊檔案。

    返回一個包含新建立任務 ID 的字典。
    """
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="不支援的檔案類型，請上傳音訊檔案。")

    task_id = await logic.create_transcription_task(file)
    return {"task_id": task_id}


@router.get("/status/{task_id}", summary="查詢轉錄任務的狀態")
async def get_task_status(
    task_id: str,
) -> dict[str, Any]:
    """
    根據任務 ID 查詢並返回其目前的狀態、進度及結果。

    - **task_id**: 必要參數，任務的唯一識別碼。

    返回一個包含任務詳細資訊的字典。如果找不到任務，則返回 404 錯誤。
    """
    task = await logic.get_task_status_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到指定的任務 ID。")
    return dict(task)

# 將此路由器註冊到核心應用程式
register_router(router)
