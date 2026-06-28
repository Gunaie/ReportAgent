"""Web 搜索工具 — Tavily Search API 封装 + 网页抓取。"""

import urllib3
import httpx
from loguru import logger
from src.config import settings

# 禁用 SSL 警告（部分网站证书过期）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    """使用 Tavily Search API 搜索网页。

    Args:
        query: 搜索查询
        max_results: 最多返回结果数

    Returns:
        [{"title": ..., "url": ..., "content": ...(摘要)}, ...]
    """
    api_key = settings.tavily_api_key
    if not api_key:
        logger.warning("未配置 TAVILY_API_KEY，使用模拟搜索结果")
        return _mock_search(query)

    try:
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
            logger.info(f"Tavily 搜索完成: {query[:30]}... → {len(results)}条结果")
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"Tavily 搜索失败: {e}")
        return _mock_search(query)


async def fetch_page(url: str) -> str:
    """抓取网页正文内容。

    Args:
        url: 网页URL

    Returns:
        提取的正文文本（最多8000字符）
    """
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ReportAgent/1.0)"
                },
                follow_redirects=True,
            )
            resp.raise_for_status()
            html = resp.text
            # 简易提取正文：去掉HTML标签
            text = _strip_html(html)
            logger.info(f"网页抓取: {url[:60]}... → {len(text)}字符")
            return text[:8000]
    except Exception as e:
        logger.warning(f"网页抓取失败 {url[:60]}...: {e}")
        return ""


def _strip_html(html: str) -> str:
    """去除 HTML 标签，保留文本。"""
    import re

    # 移除 script/style
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL)
    # 移除标签
    text = re.sub(r"<[^>]+>", " ", html)
    # 移除多余空白
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _mock_search(query: str) -> list[dict]:
    """无 API Key 时的模拟搜索结果（用于开发测试）。"""
    return [
        {
            "title": f"搜索结果1: {query}",
            "url": "https://example.com/1",
            "content": f"这是关于 '{query}' 的模拟搜索结果。在实际部署时，请配置 TAVILY_API_KEY 环境变量以启用真实搜索。",
        },
        {
            "title": f"搜索结果2: {query} - 深度分析",
            "url": "https://example.com/2",
            "content": f"关于 '{query}' 的深度分析内容。通过配置 TAVILY_API_KEY，可以获取来自真实网页的搜索结果，包括新闻、研究报告、行业分析等。",
        },
    ]
