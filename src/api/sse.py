"""SSE 端点 — Server-Sent Events 实时推送任务进度。"""

import asyncio
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from src.api.tasks import task_manager

router = APIRouter()


async def event_generator(task_id: str, request: Request) -> str:
    """SSE 事件生成器 — 从 TaskManager 订阅并 yield 事件。"""
    queue = task_manager.subscribe(task_id)
    try:
        # 先发送当前状态
        task = task_manager.get(task_id)
        if task:
            yield {"event": "status", "data": _task_to_json(task)}

        # 持续推送直到任务完成或客户端断开
        while True:
            if await request.is_disconnected():
                break
            try:
                update = await asyncio.wait_for(queue.get(), timeout=15)
                yield {"event": "status", "data": json.dumps(update, ensure_ascii=False)}
                if update.get("status") in ("done", "failed"):
                    break
            except asyncio.TimeoutError:
                # 心跳保活
                yield {"event": "heartbeat", "data": ""}
    finally:
        task_manager.unsubscribe(task_id, queue)


@router.get("/api/sse/{task_id}")
async def sse_endpoint(task_id: str, request: Request):
    """SSE 端点 — 客户端 EventSource 连接此 URL。"""
    return EventSourceResponse(event_generator(task_id, request))


def _task_to_json(task) -> str:
    """TaskInfo → JSON 字符串。"""
    import json
    return json.dumps({
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "error": task.error,
        "result": task.result,
    }, ensure_ascii=False)
