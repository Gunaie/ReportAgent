"""Agent 共享状态 — LangGraph StateGraph 的研究任务状态。"""

from typing import Any


class ResearchState(dict):
    """研究任务共享状态。

    字段说明:
        topic: 用户输入的研究主题
        refined_topic: 澄清后的精确主题
        conversation_history: 对话记录 [{role, content}]
        need_clarify: 是否需要澄清
        clarify_question: AI 提出的澄清问题
        search_results: 搜索返回的摘要列表 [{title, url, content}]
        sources: 抓取的完整网页内容 [{url, title, content}]
        trend_analysis: 趋势分析 Agent 输出
        competition_analysis: 竞争分析 Agent 输出
        risk_analysis: 风险分析 Agent 输出
        final_report: 综合报告 Markdown
        error: 错误信息
    """

    topic: str
    refined_topic: str
    conversation_history: list[dict]
    need_clarify: bool
    clarify_question: str
    search_results: list[dict]
    sources: list[dict]
    trend_analysis: str
    competition_analysis: str
    risk_analysis: str
    final_report: str
    error: str | None

    def __init__(self, topic: str = "", conversation_history: list[dict] | None = None):
        super().__init__(
            topic=topic,
            refined_topic=topic,
            conversation_history=conversation_history or [],
            need_clarify=False,
            clarify_question="",
            search_results=[],
            sources=[],
            trend_analysis="",
            competition_analysis="",
            risk_analysis="",
            final_report="",
            error=None,
        )

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value
