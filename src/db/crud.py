"""CRUD 操作 — 研报和自选股的增删改查。"""

import json
from datetime import datetime
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.db.models import Report, Task, Conversation, WatchlistItem
from src.db.engine import get_session


class ReportCRUD:
    """研报记录 CRUD。"""

    async def create(
        self,
        task_id: str,
        topic: str,
        stock_name: str = "",
        report_type: str = "single",
        rating: str | None = None,
        summary: str | None = None,
        content_md: str | None = None,
        charts: list[str] | None = None,
        output_format: str = "md",
        file_path: str | None = None,
    ) -> Report:
        """创建研报记录。

        Args:
            task_id: 任务UUID
            topic: 研究主题
            stock_name: 股票简称
            report_type: single | comparison
            rating: 综合评级
            summary: 投资摘要
            content_md: Markdown全文
            charts: 图表路径列表
            output_format: 输出格式
            file_path: 文件路径

        Returns:
            新创建的 Report 实例
        """
        report = Report(
            task_id=task_id,
            topic=topic,
            stock_name=stock_name,
            report_type=report_type,
            rating=rating,
            summary=summary,
            content_md=content_md,
            charts_json=json.dumps(charts, ensure_ascii=False) if charts else None,
            format=output_format,
            file_path=file_path,
            created_at=datetime.now(),
        )
        async with await get_session() as session:
            session.add(report)
            await session.commit()
            await session.refresh(report)
        logger.info(f"研报记录已创建: {report}")
        return report

    async def get_by_task_id(self, task_id: str) -> Report | None:
        """按任务ID查询。"""
        async with await get_session() as session:
            result = await session.execute(
                select(Report).where(Report.task_id == task_id)
            )
            return result.scalar_one_or_none()

    async def get_by_id(self, report_id: int) -> Report | None:
        """按主键查询。"""
        async with await get_session() as session:
            return await session.get(Report, report_id)

    async def list_reports(
        self,
        topic: str | None = None,
        report_type: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Report], int]:
        """分页查询研报列表。

        Args:
            topic: 按研究主题筛选（可选）
            report_type: 按类型筛选（可选）
            page: 页码（1起）
            page_size: 每页条数

        Returns:
            (报告列表, 总条数)
        """
        async with await get_session() as session:
            # 构建查询
            stmt = select(Report)
            count_stmt = select(func.count(Report.id))
            if topic:
                stmt = stmt.where(Report.topic == topic)
                count_stmt = count_stmt.where(Report.topic == topic)
            if report_type:
                stmt = stmt.where(Report.report_type == report_type)
                count_stmt = count_stmt.where(Report.report_type == report_type)
            stmt = stmt.order_by(Report.created_at.desc())

            # 总数
            total = (await session.execute(count_stmt)).scalar() or 0

            # 分页
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            reports = (await session.execute(stmt)).scalars().all()

            return list(reports), total

    async def delete(self, report_id: int) -> bool:
        """删除研报记录。"""
        async with await get_session() as session:
            result = await session.execute(
                delete(Report).where(Report.id == report_id)
            )
            await session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"研报记录已删除: id={report_id}")
            return deleted


class TaskCRUD:
    """任务状态 CRUD — 持久化管理研究任务生命周期。"""

    async def create(self, task_id: str, topic: str) -> Task:
        """创建任务记录。"""
        task = Task(task_id=task_id, topic=topic)
        async with await get_session() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)
        logger.info(f"任务已创建: {task_id} topic={topic}")
        return task

    async def update(self, task_id: str, **fields) -> Task | None:
        """部分更新任务字段。"""
        async with await get_session() as session:
            result = await session.execute(
                select(Task).where(Task.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            if task is None:
                logger.warning(f"任务不存在: {task_id}")
                return None
            for key, value in fields.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.now()
            await session.commit()
            await session.refresh(task)
        return task

    async def get(self, task_id: str) -> Task | None:
        """按 task_id 查询。"""
        async with await get_session() as session:
            result = await session.execute(
                select(Task).where(Task.task_id == task_id)
            )
            return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20) -> list[Task]:
        """查询最近的任务。"""
        async with await get_session() as session:
            result = await session.execute(
                select(Task)
                .order_by(Task.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def mark_stale_running(self) -> int:
        """将所有 running 状态的任务标记为 failed（启动恢复）。"""
        async with await get_session() as session:
            result = await session.execute(
                select(Task).where(Task.status == "running")
            )
            stale = result.scalars().all()
            for task in stale:
                task.status = "failed"
                task.error = "服务重启，任务中断"
                task.updated_at = datetime.now()
            await session.commit()
            if stale:
                logger.info(f"启动恢复: {len(stale)} 个运行中任务已标记为失败")
            return len(stale)


class ConversationCRUD:
    """对话记录 CRUD。"""

    async def add(self, task_id: str, role: str, content: str) -> Conversation:
        """添加一条对话记录。"""
        conv = Conversation(task_id=task_id, role=role, content=content)
        async with await get_session() as session:
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
        return conv

    async def get_history(self, task_id: str) -> list[Conversation]:
        """获取任务的所有对话历史（按时间正序）。"""
        async with await get_session() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.task_id == task_id)
                .order_by(Conversation.created_at.asc())
            )
            return list(result.scalars().all())


class WatchlistCRUD:
    """自选股 CRUD。"""

    async def add(self, stock_code: str, stock_name: str = "", notes: str = "") -> WatchlistItem:
        """添加自选股（重复代码则忽略）。"""
        async with await get_session() as session:
            # 检查是否已存在
            existing = await session.execute(
                select(WatchlistItem).where(WatchlistItem.stock_code == stock_code)
            )
            item = existing.scalar_one_or_none()
            if item:
                logger.info(f"自选股已存在: {stock_code}")
                return item

            item = WatchlistItem(
                stock_code=stock_code,
                stock_name=stock_name,
                notes=notes,
                added_at=datetime.now(),
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            logger.info(f"自选股已添加: {item}")
            return item

    async def list_all(self) -> list[WatchlistItem]:
        """列出所有自选股。"""
        async with await get_session() as session:
            result = await session.execute(
                select(WatchlistItem).order_by(WatchlistItem.added_at.desc())
            )
            return list(result.scalars().all())

    async def remove(self, stock_code: str) -> bool:
        """移除自选股。"""
        async with await get_session() as session:
            result = await session.execute(
                delete(WatchlistItem).where(WatchlistItem.stock_code == stock_code)
            )
            await session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"自选股已移除: {stock_code}")
            return deleted
