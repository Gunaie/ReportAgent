"""LangGraph 工作流编排 — 研究主题 → 搜索 → 三Agent分析 → 综合报告。"""

from loguru import logger
from langgraph.graph import StateGraph, END

from src.agents.state import ResearchState
from src.agents.search_agent import search_agent
from src.agents.trend_agent import trend_agent
from src.agents.competition_agent import competition_agent
from src.agents.risk_research_agent import risk_research_agent
from src.agents.synthesis_research_agent import synthesis_research_agent


def create_research_graph() -> StateGraph:
    """创建研究分析工作流。

    Flow:
        search → [trend ‖ competition ‖ risk] → synthesis → END
    """
    graph = StateGraph(ResearchState)

    # 节点
    graph.add_node("search", search_agent)
    graph.add_node("trend", trend_agent)
    graph.add_node("competition", competition_agent)
    graph.add_node("risk", risk_research_agent)
    graph.add_node("synthesis", synthesis_research_agent)

    # 入口
    graph.set_entry_point("search")

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

    logger.info("[Graph] 研究分析工作流已编译")
    return graph.compile()
