"""Web 搜索工具 — Tavily Search API 封装 + 网页抓取（含重试+降级）。"""

import httpx
from loguru import logger
from src.config import settings
from src.utils.retry import safe_call, degradation


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    """使用 Tavily Search API 搜索网页（带重试+降级）。

    Args:
        query: 搜索查询
        max_results: 最多返回结果数

    Returns:
        [{"title": ..., "url": ..., "content": ...(摘要)}, ...]
    """
    api_key = settings.tavily_api_key
    if not api_key:
        logger.warning("未配置 TAVILY_API_KEY，使用本地知识库提示")
        degradation.record_failure("tavily")
        return _local_knowledge_hint(query)

    async def _call():
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            logger.info(f"Tavily 搜索: {query[:30]}... → {len(results)}条")
            degradation.record_success("tavily")
            return [
                {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
                for r in results
            ]

    return await safe_call(
        _call,
        fallback=lambda: _local_knowledge_hint(query),
        name="Tavily搜索",
        max_attempts=2,
        base_delay=1.0,
    )


async def fetch_page(url: str) -> str:
    """抓取网页正文内容（带重试+降级）。

    Args:
        url: 网页URL

    Returns:
        提取的正文文本（最多8000字符），失败返回空字符串
    """
    async def _call():
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ReportAgent/1.0)"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            text = _strip_html(resp.text)
            logger.info(f"网页抓取: {url[:60]}... → {len(text)}字符")
            return text[:8000]

    return await safe_call(
        _call,
        fallback="",
        name=f"网页抓取({url[:50]})",
        max_attempts=2,
        base_delay=0.5,
    )


def _strip_html(html: str) -> str:
    """去除 HTML 标签，保留文本。"""
    import re
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _local_knowledge_hint(query: str) -> list[dict]:
    """搜索不可用时的本地知识提示（优雅降级）。

    返回提示信息而非模拟数据，让用户知道当前是降级模式。
    """
    degradation.record_failure("tavily")
    return [
        {
            "title": "⚠️ 实时搜索暂不可用",
            "url": "",
            "content": (
                f"Tavily 搜索服务当前不可用。请检查 TAVILY_API_KEY 配置或网络连接。\n\n"
                f"研究主题: {query}\n\n"
                "建议:\n"
                "1. 检查 .env 中 TAVILY_API_KEY 是否正确\n"
                "2. 在 https://tavily.com 确认 API 额度未耗尽\n"
                "3. 稍后重试"
            ),
        },
        {
            "title": "💡 使用离线分析模式",
            "url": "",
            "content": (
                "当前为降级模式——AI 将基于训练数据中的知识进行分析。\n"
                "注意: 分析结果可能不包含最新信息，请谨慎参考。"
            ),
        },
    ]
