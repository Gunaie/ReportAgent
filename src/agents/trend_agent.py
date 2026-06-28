"""趋势分析 Agent — 行业趋势、市场动态、政策环境（v4-flash）。"""

from langchain_core.messages import HumanMessage
from loguru import logger
from src.agents.state import ResearchState
from src.utils.model_router import create_llm
from src.utils.helpers import format_sources

TREND_PROMPT = """你是一位资深行业研究分析师。请基于以下搜索材料，从**行业趋势、市场动态、政策环境**角度进行分析。

## 研究主题
{topic}

## 搜索材料
{sources_text}

## 要求
1. 识别 3-5 个关键趋势或动态
2. 每个趋势用 2-3 句话说明，引用来源
3. 判断行业当前处于什么阶段（上升/成熟/调整/下行）
4. 使用 Markdown 格式，分点列出

## 输出格式
### 关键趋势
1. **趋势1**: 说明...
2. **趋势2**: 说明...

### 行业阶段判断
（一句话）

### 政策与监管动态
（如有相关内容）
"""


async def trend_agent(state: ResearchState) -> dict:
    """趋势分析 — 从搜索材料中提炼行业趋势。"""
    topic = state["topic"]
    logger.info(f"[趋势Agent] 分析: {topic[:40]}")

    sources = state.get("sources", [])
    sources_text = format_sources(sources)

    if not sources_text.strip():
        return {"trend_analysis": "## 行业趋势分析\n\n暂无足够的搜索材料进行分析。"}

    prompt = TREND_PROMPT.format(topic=topic, sources_text=sources_text)

    try:
        llm = create_llm("trend", temperature=0.3)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return {"trend_analysis": str(resp.content)}
    except Exception as e:
        logger.error(f"[趋势Agent] LLM失败: {e}")
        return {"trend_analysis": f"## 行业趋势分析\n\n分析失败: {e}"}


