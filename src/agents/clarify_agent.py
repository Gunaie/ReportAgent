"""澄清 Agent — 判断研究需求是否足够明确，必要时提出追问（v4-flash + 重试+降级）。"""

import json
from langchain_core.messages import HumanMessage
from loguru import logger
from src.agents.state import ResearchState
from src.utils.model_router import create_llm
from src.utils.retry import safe_call

CLARIFY_PROMPT = """你是一位资深研究顾问。你需要判断用户的研究需求是否足够明确。

## 用户输入
{topic}

## 对话历史
{history}

## 判断标准
1. 研究主题是否有明确的行业/方向？
2. 研究角度是否清晰（趋势分析/竞争格局/风险评估/综合）？
3. 范围是否合理（不过于宽泛）？

## 要求
- 如果信息充分，设置 need_clarify=false
- 如果信息不足，设置 need_clarify=true
  - 提 1 个简短、具体的中文追问（≤20字）
  - 提供 3-4 个具体的可选方向作为快捷选项（每个 ≤8字），引导用户点击
  - 选项应覆盖用户可能感兴趣的细分方向

## 输出格式（严格JSON）
{{"need_clarify": bool, "clarify_question": "...", "options": ["选项1", "选项2", "选项3"], "refined_topic": "..."}}

- need_clarify: 是否需要追问
- clarify_question: 追问内容（need_clarify=false 时为空字符串）
- options: 3-4个可选方向列表（need_clarify=false 时为空数组）
- refined_topic: 整合历史对话修正后的完整研究主题
"""


async def clarify_agent(state: ResearchState) -> dict:
    """分析研究需求，判断是否需要澄清。

    如果主题模糊（如"分析半导体"），返回追问问题。
    如果主题明确，直接通过 → search。
    """
    topic = state.get("refined_topic") or state["topic"]
    history = state.get("conversation_history", [])

    # 格式化对话历史
    history_text = ""
    for h in history[-6:]:  # 只取最近 6 轮
        role_label = "用户" if h["role"] == "user" else "助手"
        history_text += f"{role_label}: {h['content']}\n"

    if not history_text:
        history_text = "（首次对话）"

    logger.info(f"[澄清Agent] 分析: topic={topic[:40]} history_rounds={len(history)}")

    prompt = CLARIFY_PROMPT.format(topic=topic, history=history_text)

    async def _call_llm():
        llm = create_llm("clarify", temperature=0.1)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return str(resp.content).strip()

    raw = await safe_call(
        _call_llm,
        fallback="",
        name="澄清Agent",
        max_attempts=2,
        base_delay=0.5,
    )

    if not raw:
        logger.warning("[澄清Agent] LLM不可用，跳过澄清")
        return {"need_clarify": False, "clarify_question": "", "clarify_options": [], "refined_topic": topic}

    try:
        # 提取 JSON（可能被 markdown 代码块包裹）
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)
        need = result.get("need_clarify", False)
        question = result.get("clarify_question", "")
        options = result.get("options", [])
        refined = result.get("refined_topic", topic)

        # 确保 options 是列表且不超过5个
        if not isinstance(options, list):
            options = []
        options = options[:5]

        logger.info(
            f"[澄清Agent] need_clarify={need} "
            f"question={question[:30] if question else 'N/A'} "
            f"options={len(options)}"
        )
        return {
            "need_clarify": need,
            "clarify_question": question,
            "clarify_options": options,
            "refined_topic": refined or topic,
        }
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"[澄清Agent] JSON解析失败，跳过澄清: {e}")
        return {"need_clarify": False, "clarify_question": "", "clarify_options": [], "refined_topic": topic}
