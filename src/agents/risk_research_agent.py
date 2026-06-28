"""风险分析 Agent — 风险因素、不确定性、负面信号（v4-flash + 重试+降级）。"""

from langchain_core.messages import HumanMessage
from loguru import logger
from src.agents.state import ResearchState
from src.utils.model_router import create_llm
from src.utils.helpers import format_sources
from src.utils.retry import safe_call

RISK_PROMPT = """你是一位资深风控分析师。请基于以下搜索材料，识别与主题相关的**风险因素、不确定性和负面信号**。

## 研究主题
{topic}

## 搜索材料
{sources_text}

## 要求
1. 识别 3-5 个主要风险因素
2. 每个风险用 2-3 句话说明其影响和概率
3. 区分短期风险和长期风险
4. 使用 Markdown 格式

## 输出格式
### 主要风险因素
1. **风险1（短期/长期）**: 说明...
2. **风险2（短期/长期）**: 说明...

### 风险评级
- 整体风险水平: 低/中/高
- 核心不确定性: ...
"""


def _degraded_risk(topic: str, reason: str) -> str:
    """风险分析不可用时的降级输出。"""
    return (
        f"## 风险分析\n\n"
        f"> ⚠️ 风险分析暂不可用: {reason}\n\n"
        f"### 建议\n"
        f"- 稍后重试或检查 API 配置\n"
        f"- 研究主题: {topic}\n"
    )


async def risk_research_agent(state: ResearchState) -> dict:
    """风险分析（内置重试）。"""
    topic = state["topic"]
    logger.info(f"[风险Agent] 分析: {topic[:40]}")

    sources = state.get("sources", [])
    sources_text = format_sources(sources)

    if not sources_text.strip():
        return {"risk_analysis": "## 风险分析\n\n暂无足够的搜索材料进行分析。"}

    prompt = RISK_PROMPT.format(topic=topic, sources_text=sources_text)

    async def _call_llm():
        llm = create_llm("risk", temperature=0.2)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return str(resp.content)

    result = await safe_call(
        _call_llm,
        fallback=lambda: _degraded_risk(topic, "LLM调用失败"),
        name="风险Agent",
        max_attempts=2,
        base_delay=1.0,
    )
    return {"risk_analysis": result}
