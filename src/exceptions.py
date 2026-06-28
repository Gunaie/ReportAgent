"""统一异常体系 — 项目所有自定义异常的基类和分类。

设计原则:
    - 所有业务异常继承自 ReportAgentError
    - 按层次划分: 数据采集 / Agent分析 / 报告生成 / API / 数据库
    - 每个异常携带足够的上下文信息用于日志和调试
"""

from typing import Any


class ReportAgentError(Exception):
    """项目基础异常 — 所有自定义异常的根。"""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


# ====== 数据采集层 ======


class CollectionError(ReportAgentError):
    """数据采集异常 — 重试耗尽后仍失败。"""

    def __init__(self, stock_code: str, collector: str, cause: Exception | None = None):
        self.stock_code = stock_code
        self.collector = collector
        self.cause = cause
        super().__init__(
            f"采集失败: stock={stock_code} collector={collector}: {cause}",
            context={"stock_code": stock_code, "collector": collector},
        )
        if cause:
            self.__cause__ = cause


class DataParsingError(ReportAgentError):
    """数据解析异常 — akshare 返回格式与预期不符。"""

    def __init__(self, field: str, raw_value: Any, reason: str = ""):
        self.field = field
        self.raw_value = raw_value
        super().__init__(
            f"数据解析失败: field={field} value={raw_value} {reason}".strip(),
            context={"field": field, "raw_value": str(raw_value)},
        )


class DataNotAvailableError(ReportAgentError):
    """数据不可用 — 数据源无此股票数据。"""

    def __init__(self, stock_code: str, data_type: str = ""):
        self.stock_code = stock_code
        self.data_type = data_type
        super().__init__(
            f"数据不可用: stock={stock_code} type={data_type}".strip(),
            context={"stock_code": stock_code, "data_type": data_type},
        )


# ====== Agent 层 ======


class AgentError(ReportAgentError):
    """Agent 执行异常 — LLM 调用失败或返回格式不正确。"""

    def __init__(self, agent_name: str, message: str, *, cause: Exception | None = None):
        self.agent_name = agent_name
        self.cause = cause
        super().__init__(
            f"[{agent_name}] {message}",
            context={"agent_name": agent_name},
        )
        if cause:
            self.__cause__ = cause


class LLMCallError(AgentError):
    """LLM 调用失败 — API 超时/限流/返回异常。"""

    def __init__(self, agent_name: str, model: str, cause: Exception | None = None):
        self.model = model
        super().__init__(
            agent_name,
            f"LLM调用失败: model={model} error={cause}",
            cause=cause,
        )


# ====== 报告生成层 ======


class RenderError(ReportAgentError):
    """报告渲染异常 — 模板渲染或格式转换失败。"""

    def __init__(self, format_type: str, message: str, *, cause: Exception | None = None):
        self.format_type = format_type
        super().__init__(
            f"报告渲染失败 ({format_type}): {message}",
            context={"format_type": format_type},
        )
        if cause:
            self.__cause__ = cause


# ====== API 层 ======


class APIError(ReportAgentError):
    """API 层异常 — 请求参数验证/任务不存在等。"""

    def __init__(self, message: str, status_code: int = 400, *, context: dict | None = None):
        self.status_code = status_code
        super().__init__(message, context=context)


class TaskNotFoundError(APIError):
    """任务不存在。"""

    def __init__(self, task_id: str):
        super().__init__(f"任务不存在: {task_id}", status_code=404)


class InvalidStockCodeError(APIError):
    """无效的股票代码。"""

    def __init__(self, stock_code: str):
        super().__init__(f"无效的股票代码: {stock_code}", status_code=400)


# ====== 数据库层 ======


class DatabaseError(ReportAgentError):
    """数据库异常。"""

    def __init__(self, message: str, *, cause: Exception | None = None):
        super().__init__(f"数据库错误: {message}", context={})
        if cause:
            self.__cause__ = cause
            self.context["cause"] = str(cause)


# ====== 配置层 ======


class ConfigurationError(ReportAgentError):
    """配置异常 — 缺少必要的环境变量或配置无效。"""

    def __init__(self, key: str, message: str = ""):
        self.key = key
        super().__init__(
            f"配置错误: {key} — {message}".strip(" —"),
            context={"config_key": key},
        )


__all__ = [
    "ReportAgentError",
    "CollectionError",
    "DataParsingError",
    "DataNotAvailableError",
    "AgentError",
    "LLMCallError",
    "RenderError",
    "APIError",
    "TaskNotFoundError",
    "InvalidStockCodeError",
    "DatabaseError",
    "ConfigurationError",
]
