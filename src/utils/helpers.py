"""共享工具函数 — 消除跨模块代码重复。

本模块提供项目各层通用的纯函数:
    - 评级提取
    - 数值安全转换
    - 日期解析
    - 股票代码校验
"""

from datetime import date
from typing import Any


# ====== 评级提取 ======

_RATING_KEYWORDS = ["买入", "增持", "中性", "减持", "卖出"]


def extract_rating(text: str) -> str:
    """从分析文本中提取综合评级关键词。

    遍历预定义的评级列表，返回第一个匹配的关键词。
    若均不匹配，返回 "未评级"。

    Args:
        text: 分析文本（通常是 synthesis 或 comparison_analysis）

    Returns:
        评级字符串，如 "买入" / "中性" / "未评级"

    Examples:
        >>> extract_rating("综合评级: **买入**，理由...")
        '买入'
        >>> extract_rating("暂无明确结论")
        '未评级'
    """
    if not text:
        return "未评级"
    for kw in _RATING_KEYWORDS:
        if kw in text:
            return kw
    return "未评级"


def extract_summary(text: str, max_len: int = 200) -> str:
    """从分析文本中提取一段有意义的摘要。

    跳过标题行和过短的行（<20字符），返回第一段有意义的内容。

    Args:
        text: 分析文本
        max_len: 最大返回长度

    Returns:
        摘要字符串
    """
    if not text:
        return ""
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip().lstrip("#").strip()
        if len(stripped) > 20:
            return stripped[:max_len]
    return text[:max_len]


# ====== 安全数值转换 ======


def safe_float(value: Any) -> float:
    """安全转为 float，转换失败返回 0.0。

    处理 akshare 返回的空值 ("", "--", None) 和异常字符串。

    Args:
        value: 原始值，可以是 str / int / float / None

    Returns:
        float 值，失败返回 0.0

    Examples:
        >>> safe_float(None)
        0.0
        >>> safe_float("--")
        0.0
        >>> safe_float("3.14")
        3.14
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace(",", "").strip()
    if s in ("", "--", "-", "—"):
        return 0.0
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def to_float(value: Any, unit: str = "auto") -> float:
    """将 akshare 返回值转为 float，支持单位转换。

    Args:
        value: 原始值
        unit: 数值单位
            - "auto": 自动检测（>1e9 视为元→除以1e8转为亿）
            - "亿": 原始单位为亿，直接转 float
            - "%": 百分比，去掉%号转 float
            - "元": 原始单位为元，除以1e8转为亿
            - "": 不做单位转换，直接转 float

    Returns:
        转换后的 float，默认 0.0

    Examples:
        >>> to_float("91.5%", "%")
        91.5
        >>> to_float("150000000000", "元")
        1500.0
        >>> to_float("1500", "亿")
        1500.0
    """
    if value is None or value == "" or value == "--":
        return 0.0
    if isinstance(value, (int, float)):
        raw = float(value)
    else:
        clean = str(value).replace(",", "").strip()
        try:
            raw = float(clean.replace("%", ""))
        except ValueError:
            return 0.0
    if unit == "%" and isinstance(value, str):
        return raw
    if unit == "元":
        return raw / 1e8
    if unit == "auto":
        return raw / 1e8 if raw > 1e9 else raw
    if unit == "亿":
        return raw
    return raw


# ====== 日期解析 ======


def parse_date(value: Any) -> date | None:
    """安全解析日期，支持多种输入格式。

    支持的格式:
        - date 对象（直接返回）
        - "20251231" (8位数字)
        - "2025-12-31" (ISO格式)
        - "20251231T12:00:00" (前10位)
        - "2025 12 31" (空格分隔)

    Args:
        value: 日期值

    Returns:
        date 对象，解析失败返回 None
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    s = s[:10].replace(" ", "-")
    try:
        if len(s) == 8 and s.isdigit():
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# ====== 股票代码验证 ======

_STOCK_CODE_PATTERN = {
    "SH": r"^6\d{5}$",  # 上交所: 60xxxx
    "SZ": r"^00\d{4}$|^30\d{4}$",  # 深交所: 00xxxx / 30xxxx (创业板)
    "BJ": r"^8\d{5}$|^4\d{5}$",  # 北交所: 8xxxxx / 4xxxxx
}


def validate_stock_code(code: str) -> bool:
    """验证 A 股股票代码格式。

    Args:
        code: 股票代码字符串

    Returns:
        是否有效

    Examples:
        >>> validate_stock_code("600519")
        True
        >>> validate_stock_code("abc123")
        False
    """
    import re

    if not code or not isinstance(code, str):
        return False
    code = code.strip()
    if not code.isdigit() or len(code) != 6:
        return False
    for pattern in _STOCK_CODE_PATTERN.values():
        if re.match(pattern, code):
            return True
    return False


def get_market(code: str) -> str:
    """根据股票代码推断交易所。

    Args:
        code: 6位股票代码

    Returns:
        "SH" / "SZ" / "BJ" / "未知"
    """
    if not validate_stock_code(code):
        return "未知"
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("8", "4")):
        return "BJ"
    return "未知"


# ====== 来源格式化 ======


def format_sources(sources: list[dict], max_content_len: int = 3000) -> str:
    """将搜索来源列表格式化为 Agent 可读文本。

    Args:
        sources: 来源列表 [{title, url, content}, ...]
        max_content_len: 每个来源内容的最大字符数

    Returns:
        格式化后的文本，每个来源以 "### 来源N: ..." 开头
    """
    parts = []
    for i, s in enumerate(sources, 1):
        parts.append(
            f"### 来源{i}: {s.get('title', '无标题')}\n"
            f"URL: {s.get('url', '')}\n"
            f"内容:\n{s.get('content', '')[:max_content_len]}\n"
        )
    return "\n\n".join(parts) if parts else ""


__all__ = [
    "extract_rating",
    "extract_summary",
    "safe_float",
    "to_float",
    "parse_date",
    "validate_stock_code",
    "get_market",
    "format_sources",
]
