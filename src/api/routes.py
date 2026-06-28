"""REST 路由 — 研究分析/查询/历史。"""

import asyncio
import json
from loguru import logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from src.api.tasks import task_manager
from src.agents.graph import create_research_graph
from src.agents.state import ResearchState
from src.db import ReportCRUD
from src.generator import ReportRenderer
from src.utils.helpers import extract_rating, extract_summary

router = APIRouter()


# ====== 请求模型 ======

class ResearchRequest(BaseModel):
    topic: str = ""

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 4:
            raise ValueError("研究主题至少需要4个字符")
        return v


# ====== 研究任务 ======

@router.post("/api/research")
async def research(req: ResearchRequest):
    """提交研究分析任务。"""
    task = task_manager.create(req.topic)
    bg = asyncio.create_task(_run_research(task.task_id, req.topic))
    bg.add_done_callback(_handle_task_error)
    return {"task_id": task.task_id, "status": "pending"}


@router.get("/api/task/{task_id}")
async def get_task(task_id: str):
    """查询任务状态。"""
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(404, "任务不存在")
    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "error": task.error,
        "result": task.result,
    }


# ====== 报告查询 ======

@router.get("/api/reports")
async def list_reports(page: int = 1, size: int = 10):
    """分页查询历史报告。"""
    crud = ReportCRUD()
    items, total = await crud.list_reports(page=page, page_size=size)
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "topic": r.topic,
                "stock_name": r.stock_name,
                "report_type": r.report_type,
                "rating": r.rating,
                "summary": r.summary,
                "created_at": str(r.created_at),
            }
            for r in items
        ],
    }


@router.get("/api/reports/{task_id}/content")
async def get_report_content(task_id: str):
    """获取报告 Markdown 全文。"""
    crud = ReportCRUD()
    report = await crud.get_by_task_id(task_id)
    if report is None:
        raise HTTPException(404, "报告不存在")
    return {
        "task_id": report.task_id,
        "topic": report.topic,
        "rating": report.rating,
        "summary": report.summary,
        "content": report.content_md,
        "created_at": str(report.created_at) if report.created_at else None,
    }


# ====== 内部执行逻辑 ======

_NODE_PROGRESS: dict[str, tuple[float, str]] = {
    "search": (0.25, "搜索完成，正在分析…"),
    "trend": (0.45, "趋势分析完成"),
    "competition": (0.60, "竞争分析完成"),
    "risk": (0.75, "风险分析完成"),
    "synthesis": (0.92, "报告生成完成"),
}


async def _run_research(task_id: str, topic: str):
    """后台执行研究分析 — 通过 astream 获取逐节点进度。"""
    tm = task_manager
    try:
        tm.update(task_id, status="running", progress=0.05, current_step="搜索中…")

        graph = create_research_graph()
        state = ResearchState(topic=topic)

        # 使用 astream 获取进度
        result_state = state
        async for event in graph.astream(state):
            for node_name, node_output in event.items():
                result_state.update(node_output)
                if node_name in _NODE_PROGRESS:
                    prog, desc = _NODE_PROGRESS[node_name]
                    tm.update(task_id, progress=prog, current_step=desc)

        if result_state.get("error"):
            tm.update(task_id, status="failed", error=result_state["error"])
            return

        tm.update(task_id, progress=0.95, current_step="保存报告…")

        crud = ReportCRUD()
        renderer = ReportRenderer()
        md = result_state.get("final_report") or renderer.render_single(result_state)

        # 写入文件
        file_path = renderer.save_markdown(md, topic[:30].replace(" ", "_"))

        # 提取摘要
        synthesis = result_state.get("synthesis_analysis", "")
        summary = extract_summary(synthesis, max_len=200)

        await crud.create(
            task_id=task_id,
            topic=topic,
            stock_name=topic[:50],
            report_type="research",
            rating=None,
            summary=summary,
            content_md=md,
            file_path=file_path,
        )

        # 获取搜索来源
        sources = result_state.get("sources", [])
        source_urls = [s.get("url", "") for s in sources if s.get("url")]

        tm.update(
            task_id, status="done", progress=1.0, current_step="完成",
            result={
                "topic": topic,
                "summary": summary,
                "file_path": file_path,
                "sources": source_urls,
            },
        )
    except Exception as e:
        logger.exception(f"研究分析异常: {task_id}")
        tm.update(task_id, status="failed", error=str(e))


def _handle_task_error(fut: asyncio.Task) -> None:
    """后台任务异常兜底。"""
    if not fut.cancelled() and fut.exception():
        logger.error(f"后台任务异常: {fut.exception()}")
