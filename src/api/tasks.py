"""异步任务管理 — 内存任务队列，跟踪分析任务状态。"""

import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class TaskInfo:
    """单个分析任务的状态。"""

    task_id: str
    topic: str
    status: str = "pending"         # pending | running | done | failed
    progress: float = 0.0           # 0.0 ~ 1.0
    current_step: str = ""
    result: dict | None = None      # 完成后的结果
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TaskManager:
    """内存任务管理器。

    管理分析任务的完整生命周期，通过 SSE 推送状态变更。
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def create(self, topic: str) -> TaskInfo:
        """创建新任务。"""
        task_id = str(uuid.uuid4())
        task = TaskInfo(task_id=task_id, topic=topic)
        self._tasks[task_id] = task
        logger.info(f"任务已创建: {task_id} topic={topic}")
        return task

    def update(self, task_id: str, **kwargs) -> TaskInfo | None:
        """更新任务状态并通知订阅者。"""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        for key, value in kwargs.items():
            setattr(task, key, value)
        self._notify(task_id, task)
        return task

    def get(self, task_id: str) -> TaskInfo | None:
        """获取任务信息。"""
        return self._tasks.get(task_id)

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """订阅任务状态变更（SSE消费）。"""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(task_id, []).append(q)
        return q

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """取消订阅。"""
        subs = self._subscribers.get(task_id, [])
        if queue in subs:
            subs.remove(queue)

    def _notify(self, task_id: str, task: TaskInfo) -> None:
        """向所有订阅者推送状态。"""
        subs = self._subscribers.get(task_id, [])
        for q in subs:
            q.put_nowait({
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "error": task.error,
                "result": task.result,
            })


# 全局单例
task_manager = TaskManager()
