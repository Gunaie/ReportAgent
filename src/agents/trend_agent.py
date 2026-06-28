"""趋势分析 Agent — 行业趋势、市场动态、政策环境（v4-flash + 重试+降级）。"""

from langchain_core.messages import HumanMessage
from loguru import logger
from src.agents.state import ResearchState
from src.utils.model_router import create_llm
from src.utils.helpers import format_sources
from src.utils.retry import safe_call

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


def _degraded_trend(topic: str, reason: str) -> str:
    """趋势分析不可用时的降级输出。"""
    return (
        f"## 行业趋势分析\n\n"
        f"> ⚠️ 趋势分析暂不可用: {reason}\n\n"
        f"### 建议\n"
        f"- 稍后重试或缩小研究范围\n"
        f"- 检查 DashScope API 配置和额度\n"
        f"- 研究主题: {topic}\n"
    )


async def trend_agent(state: ResearchState) -> dict:
    """趋势分析 — 从搜索材料中提炼行业趋势（内置重试）。"""
    topic = state["topic"]
    logger.info(f"[趋势Agent] 分析: {topic[:40]}")

    sources = state.get("sources", [])
    sources_text = format_sources(sources)

    if not sources_text.strip():
        return {"trend_analysis": "## 行业趋势分析\n\n暂无足够的搜索材料进行分析。"}

    prompt = TREND_PROMPT.format(topic=topic, sources_text=sources_text)

    async def _call_llm():
        llm = create_llm("trend", temperature=0.3)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return str(resp.content)

    result = await safe_call(
        _call_llm,
        fallback=lambda: _degraded_trend(topic, "LLM调用失败"),
        name="趋势Agent",
        max_attempts=2,
        base_delay=1.0,
    )
    return {"trend_analysis": result}
