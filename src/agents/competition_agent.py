"""竞争分析 Agent — 公司对比、竞争格局、市场份额（v4-pro）。"""

from langchain_core.messages import HumanMessage
from loguru import logger
from src.agents.state import ResearchState
from src.utils.model_router import create_llm
from src.utils.helpers import format_sources

COMPETITION_PROMPT = """你是一位资深竞争战略分析师。请基于以下搜索材料，从**竞争格局、公司对比、市场份额**角度进行分析。

## 研究主题
{topic}

## 搜索材料
{sources_text}

## 要求
1. 识别主要参与者和竞争格局
2. 对比头部公司的优劣势
3. 分析市场份额变化或竞争动态
4. 使用 Markdown 格式，包含对比表格（如有数据）

## 输出格式
### 竞争格局概览
- 主要参与者: ...
- 市场集中度: ...

### 头部公司对比
（如有多家公司数据，用 Markdown 表格列出关键对比维度）

### 竞争动态
- 近期重要变化...
"""


async def competition_agent(state: ResearchState) -> dict:
    """竞争分析 — 使用 v4-pro 深度推理。"""
    topic = state["topic"]
    logger.info(f"[竞争Agent] v4-pro 分析: {topic[:40]}")

    sources = state.get("sources", [])
    sources_text = format_sources(sources)

    if not sources_text.strip():
        return {"competition_analysis": "## 竞争格局分析\n\n暂无足够的搜索材料进行分析。"}

    prompt = COMPETITION_PROMPT.format(topic=topic, sources_text=sources_text)

    try:
        llm = create_llm("competition", temperature=0.2)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return {"competition_analysis": str(resp.content)}
    except Exception as e:
        logger.error(f"[竞争Agent] LLM失败: {e}")
        return {"competition_analysis": f"## 竞争格局分析\n\n分析失败: {e}"}


