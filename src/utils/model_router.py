"""模型路由器 — 按任务复杂度分配 v4-flash(70%) vs v4-pro(30%)。"""

from enum import Enum
from langchain_openai import ChatOpenAI
from src.config import settings


class TaskTier(str, Enum):
    """任务层级：SIMPLE → v4-flash, COMPLEX → v4-pro。"""
    SIMPLE = "simple"
    COMPLEX = "complex"


# 模型名称 → 实际 model ID 的映射
_MODEL_MAP = {
    TaskTier.SIMPLE: settings.flash_model,
    TaskTier.COMPLEX: settings.pro_model,
}

# Agent 名称 → 任务层级映射
_AGENT_TIER = {
    "clarify": TaskTier.SIMPLE,
    "search": TaskTier.SIMPLE,
    "trend": TaskTier.SIMPLE,
    "competition": TaskTier.COMPLEX,
    "risk": TaskTier.SIMPLE,
    "synthesis": TaskTier.COMPLEX,
    "default": TaskTier.SIMPLE,
}


def get_model_for_agent(agent_name: str) -> str:
    """根据 Agent 名称返回应使用的模型 ID。"""
    tier = _AGENT_TIER.get(agent_name, TaskTier.SIMPLE)
    return _MODEL_MAP[tier]


def create_llm(agent_name: str = "default", temperature: float = 0.3) -> ChatOpenAI:
    """创建 LangChain ChatOpenAI 实例，自动路由到对应模型。

    Args:
        agent_name: Agent 标识 (finance/valuation/risk/comparison/synthesis)
        temperature: 采样温度，分析类任务建议 0.1~0.3

    Returns:
        配置好的 ChatOpenAI 实例
    """
    model = get_model_for_agent(agent_name)
    return ChatOpenAI(
        model=model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        temperature=temperature,
        max_tokens=4096,
    )
