# -*- coding: utf-8 -*-
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.phoenix_core.modules.prometheus_pipeline.core.logging.log_manager import LogManager

# 暫時使用全域 logger，後續可以替換為模組專用的
# from phoenix_core.utils.logger import logger
logger = LogManager.get_instance().get_logger("PrometheusRouter")

router = APIRouter(
    prefix="/prometheus",
    tags=["Prometheus Pipeline"],
)

class PipelineRequest(BaseModel):
    pipeline_name: str
    force_run: bool = False

@router.post("/run-pipeline", status_code=202)
async def run_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
):
    """
    觸發一個普羅米修斯數據管線的背景執行。

    - **pipeline_name**: 要執行的管線名稱 (例如 "build-feature-store")。
    - **force_run**: 是否強制重新執行，即使數據已存在。
    """
    logger.info(f"收到執行管線 '{request.pipeline_name}' 的請求...")

    # TODO: 在這裡添加將任務放入背景佇列的邏輯
    # from .worker import add_pipeline_task
    # background_tasks.add_task(add_pipeline_task, request.pipeline_name)

    logger.info("請求已接受，將在背景開始執行。")
    return {"message": "Pipeline run accepted and will be processed in the background.", "pipeline_name": request.pipeline_name}
