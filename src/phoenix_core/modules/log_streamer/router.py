# -*- coding: utf-8 -*-
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

from ...database import db_manager
from ...kernel.registry import registered_routers

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"],
)

@router.websocket("/logs")
async def websocket_log_endpoint(websocket: WebSocket):
    """
    Provide a WebSocket endpoint to stream logs in real-time.
    """
    await websocket.accept()
    last_check_time = datetime.now(timezone.utc)

    try:
        while True:
            logs = db_manager.get_logs_since(last_check_time)

            if logs:
                last_log_timestamp_str = logs[-1]['timestamp']
                last_check_time = datetime.fromisoformat(last_log_timestamp_str)
                await websocket.send_json(logs)

            await asyncio.sleep(1.5)

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"An error occurred in the WebSocket: {e}")
        await websocket.close(code=1011)

registered_routers.append(router)
