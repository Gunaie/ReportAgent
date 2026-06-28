"""搜索 Agent — Web 搜索 + 网页内容抓取。"""

import asyncio
from loguru import logger
from src.agents.state import ResearchState
from src.tools.web_search import search_web, fetch_page


async def search_agent(state: ResearchState) -> dict:
    """执行 Web 搜索并抓取 Top 3 结果的内容。

    Args:
        state: 包含 topic

    Returns:
        {"search_results": [...], "sources": [...]}
    """
    topic = state["topic"]
    logger.info(f"[搜索Agent] 搜索: {topic}")

    try:
        # Step 1: 搜索
        results = await search_web(topic, max_results=5)
        state["search_results"] = results

        # Step 2: 并行抓取 Top 3 网页内容
        top_urls = [r["url"] for r in results[:3] if r.get("url")]
        if top_urls:
            pages = await asyncio.gather(
                *[fetch_page(url) for url in top_urls],
                return_exceptions=True,
            )
            sources = []
            for i, page in enumerate(pages):
                if isinstance(page, Exception):
                    logger.warning(f"抓取失败 {top_urls[i]}: {page}")
                    continue
                if page:
                    sources.append({
                        "url": top_urls[i],
                        "title": results[i].get("title", ""),
                        "content": page,
                    })
            logger.info(f"[搜索Agent] 抓取完成: {len(sources)}/{len(top_urls)} 个网页")
            return {"sources": sources}

        return {"sources": []}
    except Exception as e:
        logger.error(f"[搜索Agent] 失败: {e}")
        return {"error": str(e), "search_results": [], "sources": []}
