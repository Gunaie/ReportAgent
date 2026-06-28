"""风险分析 Agent — 风险因素、不确定性、负面信号（v4-flash）。"""

from langchain_core.messages import HumanMessage
from loguru import logger
from src.agents.state import ResearchState
from src.utils.model_router import create_llm
from src.utils.helpers import format_sources

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


async def risk_research_agent(state: ResearchState) -> dict:
    """风险分析。"""
    topic = state["topic"]
    logger.info(f"[风险Agent] 分析: {topic[:40]}")

    sources = state.get("sources", [])
    sources_text = format_sources(sources)

    if not sources_text.strip():
        return {"risk_analysis": "## 风险分析\n\n暂无足够的搜索材料进行分析。"}

    prompt = RISK_PROMPT.format(topic=topic, sources_text=sources_text)

    try:
        llm = create_llm("risk", temperature=0.2)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return {"risk_analysis": str(resp.content)}
    except Exception as e:
        logger.error(f"[风险Agent] LLM失败: {e}")
        return {"risk_analysis": f"## 风险分析\n\n分析失败: {e}"}


