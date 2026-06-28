"""AI Agent 层 — LangGraph 多Agent研究编排。

工作流:
  搜索 → [趋势分析 ‖ 竞争分析 ‖ 风险分析] → 综合报告
"""

from src.agents.state import ResearchState
from src.agents.graph import create_research_graph

__all__ = [
    "ResearchState",
    "create_research_graph",
]
