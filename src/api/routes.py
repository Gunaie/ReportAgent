"""REST 路由 — 研究分析/对话/查询/历史。"""

from loguru import logger
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, field_validator

from src.api.tasks import task_manager
from src.agents.graph import create_research_graph
from src.agents.state import ResearchState
from src.db import ReportCRUD
from src.db.crud import ConversationCRUD
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


class ContinueRequest(BaseModel):
    task_id: str
    user_reply: str

    @field_validator("user_reply")
    @classmethod
    def validate_reply(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("回复至少需要2个字符")
        return v


# ====== 研究任务 ======

@router.post("/api/research")
async def research(req: ResearchRequest, bg: BackgroundTasks):
    """提交研究分析任务。

    先经澄清Agent判断需求是否明确：
    - 如果需要澄清 → 返回 clarify_question，等待用户回复
    - 如果需求明确 → 直接进入搜索分析
    """
    task = await task_manager.create(req.topic)

    # 保存用户输入到对话历史
    await ConversationCRUD().add(task.task_id, "user", req.topic)

    bg.add_task(_run_research, task.task_id, req.topic)
    return {"task_id": task.task_id, "status": "pending"}


@router.post("/api/research/continue")
async def research_continue(req: ContinueRequest, bg: BackgroundTasks):
    """继续对话式研究 — 用户回复澄清问题后调用。"""
    task = await task_manager.get(req.task_id)
    if task is None:
        raise HTTPException(404, "任务不存在")
    if task.status not in ("clarifying",):
        raise HTTPException(400, f"任务状态为 {task.status}，无法继续对话")

    # 保存用户回复
    await ConversationCRUD().add(req.task_id, "user", req.user_reply)

    # 获取对话历史
    conv_crud = ConversationCRUD()
    history_rows = await conv_crud.get_history(req.task_id)
    history = [{"role": h.role, "content": h.content} for h in history_rows]

    # 后台继续执行
    await task_manager.update(req.task_id, status="running", progress=0.02, current_step="分析需求…")
    bg.add_task(_run_research, req.task_id, task.topic, conversation_history=history)
    return {"task_id": req.task_id, "status": "running"}


@router.get("/api/task/{task_id}")
async def get_task(task_id: str):
    """查询任务状态。"""
    task = await task_manager.get(task_id)
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


# ====== 对话历史 ======

@router.get("/api/conversation/{task_id}")
async def get_conversation(task_id: str):
    """获取任务的对话历史。"""
    rows = await ConversationCRUD().get_history(task_id)
    return {
        "task_id": task_id,
        "messages": [
            {"role": r.role, "content": r.content, "time": str(r.created_at)}
            for r in rows
        ],
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
    "clarify": (0.02, "分析研究需求…"),
    "search": (0.25, "搜索完成，正在分析…"),
    "trend": (0.45, "趋势分析完成"),
    "competition": (0.60, "竞争分析完成"),
    "risk": (0.75, "风险分析完成"),
    "synthesis": (0.92, "报告生成完成"),
}


async def _run_research(
    task_id: str,
    topic: str,
    conversation_history: list[dict] | None = None,
):
    """后台执行研究分析 — 含澄清阶段。"""
    tm = task_manager
    conv_crud = ConversationCRUD()
    try:
        graph = create_research_graph()
        state = ResearchState(
            topic=topic,
            conversation_history=conversation_history or [],
        )

        # 运行图（可能停在 clarify 或走到 synthesis）
        result_state = state
        async for event in graph.astream(state):
            for node_name, node_output in event.items():
                result_state.update(node_output)

                # 检查 clarify 节点：是否需要追问
                if node_name == "clarify":
                    if result_state.get("need_clarify"):
                        question = result_state.get("clarify_question", "请补充更多信息")
                        refined = result_state.get("refined_topic", topic)
                        await conv_crud.add(task_id, "assistant", question)
                        await tm.update(
                            task_id,
                            status="clarifying",
                            progress=0.02,
                            current_step="等待用户回复",
                            result={
                                "clarify_question": question,
                                "refined_topic": refined,
                            },
                        )
                        return  # 暂停，等待 /research/continue

                # 普通进度更新
                if node_name in _NODE_PROGRESS:
                    prog, desc = _NODE_PROGRESS[node_name]
                    await tm.update(task_id, progress=prog, current_step=desc)

        # clarify 通过 → 检查错误
        if result_state.get("error"):
            await tm.update(task_id, status="failed", error=result_state["error"])
            return

        # 生成报告
        await tm.update(task_id, progress=0.95, current_step="保存报告…")

        crud = ReportCRUD()
        renderer = ReportRenderer()
        refined = result_state.get("refined_topic") or topic
        md = result_state.get("final_report") or renderer.render_single(result_state)

        # 写入文件
        safe_name = refined[:30].replace(" ", "_")
        file_path = renderer.save_markdown(md, safe_name)

        # 提取摘要
        synthesis = result_state.get("synthesis_analysis", "")
        summary = extract_summary(synthesis, max_len=200)

        await crud.create(
            task_id=task_id,
            topic=refined,
            stock_name=refined[:50],
            report_type="research",
            rating=None,
            summary=summary,
            content_md=md,
            file_path=file_path,
        )

        # 保存 AI 回复到对话历史
        await conv_crud.add(task_id, "assistant", f"报告已生成：{summary}")

        # 获取搜索来源
        sources = result_state.get("sources", [])
        source_urls = [s.get("url", "") for s in sources if s.get("url")]

        await tm.update(
            task_id, status="done", progress=1.0, current_step="完成",
            result={
                "topic": refined,
                "summary": summary,
                "file_path": file_path,
                "sources": source_urls,
            },
        )
    except Exception as e:
        logger.exception(f"研究分析异常: {task_id}")
        await tm.update(task_id, status="failed", error=str(e))


