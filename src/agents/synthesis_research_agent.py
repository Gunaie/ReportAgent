"""综合研究 Agent — 汇总所有分析，生成完整研究报告（v4-pro）。"""

from langchain_core.messages import HumanMessage
from loguru import logger
from src.agents.state import ResearchState
from src.utils.model_router import create_llm

SYNTHESIS_PROMPT = """你是一位首席研究员。请综合以下三份分析报告，撰写一份完整的研究报告。

## 研究主题
{topic}

## 趋势分析
{trend}

## 竞争分析
{competition}

## 风险分析
{risk}

## 要求
生成一份包含以下章节的 Markdown 报告：

### 1. 摘要
用 3 句话概括核心发现

### 2. 行业趋势
（整合趋势分析的要点）

### 3. 竞争格局
（整合竞争分析的要点）

### 4. 风险提示
（整合风险分析的要点）

### 5. 综合结论
- 对研究主题给出明确判断
- 3-5 条核心建议

### 6. 信息来源
列出研究中引用的来源。如果有具体的 URL，请列出。
"""


async def synthesis_research_agent(state: ResearchState) -> dict:
    """汇总研究（v4-pro 深度推理）。"""
    topic = state["topic"]
    logger.info(f"[综合Agent] v4-pro 汇总: {topic[:40]}")

    trend = state.get("trend_analysis", "未完成")
    competition = state.get("competition_analysis", "未完成")
    risk = state.get("risk_analysis", "未完成")

    # 检测上游故障：全部失败 → 跳过 LLM，直接返回错误报告
    failed = all(
        "分析失败" in (v or "")
        for v in (trend, competition, risk)
    )
    if failed:
        logger.error("[综合Agent] 三个上游Agent全部失败，中止汇总")
        error_report = _error_report(state)
        return {
            "synthesis_analysis": "综合汇总中止：上游分析全部失败",
            "final_report": error_report,
        }

    prompt = SYNTHESIS_PROMPT.format(topic=topic, trend=trend, competition=competition, risk=risk)

    try:
        llm = create_llm("synthesis", temperature=0.15)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        synthesis = str(resp.content)

        return {
            "synthesis_analysis": synthesis,
            "final_report": _assemble_report(state, synthesis),
        }
    except Exception as e:
        logger.error(f"[综合Agent] LLM失败: {e}")
        error_report = _error_report(state, error=str(e))
        return {
            "synthesis_analysis": f"综合汇总失败: {e}",
            "final_report": error_report,
        }


def _error_report(state: ResearchState, error: str = "") -> str:
    """生成错误报告 — 明确告知用户分析失败，不伪装成功。"""
    topic = state["topic"]
    parts = [
        f"# 研究报告: {topic}",
        f"\n> ⚠️ 报告生成失败",
        "",
        "---",
        "",
        "## 失败原因",
        "",
    ]
    if error:
        parts.append(f"综合汇总阶段出错: {error}")
    else:
        parts.append("上游分析（趋势/竞争/风险）全部失败，无法生成综合报告。")
        parts.append("")
        parts.append("请尝试：")
        parts.append("- 更换更具体的研究主题")
        parts.append("- 检查网络连接和 API 配置")
        parts.append("- 稍后重试")
    parts.append("")
    return "\n\n".join(parts)


def _assemble_report(state: ResearchState, synthesis: str) -> str:
    """组装完整 Markdown 报告。综合汇总已涵盖所有分析，不再重复子Agent输出。"""
    topic = state["topic"]
    sources = state.get("sources", [])

    parts = [
        f"# 研究报告: {topic}",
        f"\n> 生成时间: 自动 | 免责声明: 本报告由AI自动生成，基于公开信息搜索和分析，仅供参考\n",
        "---",
        synthesis,
    ]

    # 信息来源
    if sources:
        parts.append("\n---\n")
        parts.append("## 📚 参考来源\n")
        for i, s in enumerate(sources, 1):
            parts.append(f"{i}. [{s.get('title', '来源')}]({s.get('url', '')})")

    parts.append(
        "\n\n*本报告由AI自动生成，基于公开信息搜索和分析。报告内容仅供研究参考，不构成投资建议。*"
    )
    return "\n\n".join(parts)
