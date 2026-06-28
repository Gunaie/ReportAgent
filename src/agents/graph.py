"""LangGraph 工作流编排 — 对话式研究：澄清 → 搜索 → 三Agent → 综合报告。"""

from loguru import logger
from langgraph.graph import StateGraph, END

from src.agents.state import ResearchState
from src.agents.clarify_agent import clarify_agent
from src.agents.search_agent import search_agent
from src.agents.trend_agent import trend_agent
from src.agents.competition_agent import competition_agent
from src.agents.risk_research_agent import risk_research_agent
from src.agents.synthesis_research_agent import synthesis_research_agent


def _route_after_clarify(state: ResearchState) -> str:
    """条件路由：需要澄清 → 暂停等待用户输入；不需要 → 开始搜索。"""
    if state.get("need_clarify"):
        logger.info("[Graph] 需要澄清，等待用户回复")
        return END
    logger.info("[Graph] 需求明确，开始搜索")
    return "search"


def create_research_graph() -> StateGraph:
    """创建研究分析工作流。

    Flow (对话式):
        clarify → [need_clarify? → END(等待回复)]
                 → [明确 → search → [trend‖competition‖risk] → synthesis → END]

    三个分析 Agent 自带兜底（无搜索结果时返回提示），因此 search 无需条件路由。
    """
    graph = StateGraph(ResearchState)

    # 节点
    graph.add_node("clarify", clarify_agent)
    graph.add_node("search", search_agent)
    graph.add_node("trend", trend_agent)
    graph.add_node("competition", competition_agent)
    graph.add_node("risk", risk_research_agent)
    graph.add_node("synthesis", synthesis_research_agent)

    # 入口
    graph.set_entry_point("clarify")

    # clarify → 条件路由：需要澄清 → END；明确 → search
    graph.add_conditional_edges("clarify", _route_after_clarify, {
        "search": "search",
        END: END,
    })

    # search → 并行 fan-out 到三个分析 Agent
    graph.add_edge("search", "trend")
    graph.add_edge("search", "competition")
    graph.add_edge("search", "risk")

    # fan-in → synthesis
    graph.add_edge("trend", "synthesis")
    graph.add_edge("competition", "synthesis")
    graph.add_edge("risk", "synthesis")

    # synthesis → END
    graph.add_edge("synthesis", END)

    logger.info("[Graph] 对话式研究工作流已编译")
    return graph.compile()
