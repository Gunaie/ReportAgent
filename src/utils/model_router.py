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

# Agent 名称 → (任务层级, 超时秒数) 映射
_AGENT_CONFIG: dict[str, tuple[TaskTier, int]] = {
    "clarify":     (TaskTier.SIMPLE,  30),
    "search":      (TaskTier.SIMPLE,  45),
    "trend":       (TaskTier.SIMPLE,  60),
    "competition": (TaskTier.COMPLEX, 120),
    "risk":        (TaskTier.SIMPLE,  60),
    "synthesis":   (TaskTier.COMPLEX, 120),
    "default":     (TaskTier.SIMPLE,  60),
}


def get_model_for_agent(agent_name: str) -> str:
    """根据 Agent 名称返回应使用的模型 ID。"""
    tier, _ = _AGENT_CONFIG.get(agent_name, (TaskTier.SIMPLE, 60))
    return _MODEL_MAP[tier]


def get_timeout_for_agent(agent_name: str) -> int:
    """根据 Agent 名称返回 LLM 调用超时秒数。"""
    _, timeout = _AGENT_CONFIG.get(agent_name, (TaskTier.SIMPLE, 60))
    return timeout


def create_llm(agent_name: str = "default", temperature: float = 0.3) -> ChatOpenAI:
    """创建 LangChain ChatOpenAI 实例，自动路由到对应模型。

    Args:
        agent_name: Agent 标识 (finance/valuation/risk/comparison/synthesis)
        temperature: 采样温度，分析类任务建议 0.1~0.3

    Returns:
        配置好的 ChatOpenAI 实例
    """
    model = get_model_for_agent(agent_name)
    timeout = get_timeout_for_agent(agent_name)
    return ChatOpenAI(
        model=model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        temperature=temperature,
        max_tokens=4096,
        request_timeout=timeout,
    )
