"""异步任务管理 — DB 持久化状态 + 内存 SSE 订阅。

服务重启后任务状态不丢失：DB 是数据权威来源，SSE 订阅者保持内存模式。
"""

import uuid
import json
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from src.db.crud import TaskCRUD


@dataclass
class TaskInfo:
    """单个分析任务的内存视图。"""

    task_id: str
    topic: str
    status: str = "pending"         # pending | running | done | failed
    progress: float = 0.0           # 0.0 ~ 1.0
    current_step: str = ""
    result: dict | None = None      # 完成后的结果
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TaskManager:
    """持久化任务管理器。

    - 任务状态写入 DB（SQLAlchemy → SQLite/PostgreSQL）
    - SSE 订阅者队列保持内存模式（业界标准）
    """

    def __init__(self) -> None:
        self._crud = TaskCRUD()
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    # ====== 任务生命周期 ======

    async def create(self, topic: str) -> TaskInfo:
        """创建新任务（写 DB）。"""
        task_id = str(uuid.uuid4())
        db_task = await self._crud.create(task_id=task_id, topic=topic)
        logger.info(f"任务已创建: {task_id} topic={topic}")
        return self._to_info(db_task)

    async def update(self, task_id: str, **kwargs) -> TaskInfo | None:
        """更新任务状态（写 DB）并通知 SSE 订阅者。"""
        # 序列化 result
        if "result" in kwargs and kwargs["result"] is not None:
            kwargs["result_json"] = json.dumps(kwargs.pop("result"), ensure_ascii=False)

        db_task = await self._crud.update(task_id, **kwargs)
        if db_task is None:
            return None

        info = self._to_info(db_task)
        self._notify(task_id, info)
        return info

    async def get(self, task_id: str) -> TaskInfo | None:
        """查询任务（读 DB）。"""
        db_task = await self._crud.get(task_id)
        if db_task is None:
            return None
        return self._to_info(db_task)

    # ====== SSE 订阅（纯内存） ======

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """订阅任务状态变更（SSE 消费端调用）。"""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(task_id, []).append(q)
        return q

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """取消订阅。"""
        subs = self._subscribers.get(task_id, [])
        if queue in subs:
            subs.remove(queue)

    # ====== 内部 ======

    def _notify(self, task_id: str, info: TaskInfo) -> None:
        """向所有订阅者推送状态。"""
        subs = self._subscribers.get(task_id, [])
        for q in subs:
            q.put_nowait({
                "task_id": info.task_id,
                "status": info.status,
                "progress": info.progress,
                "current_step": info.current_step,
                "error": info.error,
                "result": info.result,
            })

    @staticmethod
    def _to_info(db_task) -> TaskInfo:
        """ORM → TaskInfo 视图。"""
        result = None
        if db_task.result_json:
            try:
                result = json.loads(db_task.result_json)
            except json.JSONDecodeError:
                pass
        return TaskInfo(
            task_id=db_task.task_id,
            topic=db_task.topic,
            status=db_task.status,
            progress=db_task.progress,
            current_step=db_task.current_step,
            result=result,
            error=db_task.error,
            created_at=db_task.created_at.isoformat() if db_task.created_at else "",
        )


# 全局单例
task_manager = TaskManager()
