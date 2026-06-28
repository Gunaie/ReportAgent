"""搜索 Agent — Web 搜索 + 网页内容抓取（含重试+降级）。"""

import asyncio
from loguru import logger
from src.agents.state import ResearchState
from src.tools.web_search import search_web, fetch_page


async def search_agent(state: ResearchState) -> dict:
    """执行 Web 搜索并抓取 Top 3 结果的内容。

    Tavily 搜索失败时自动降级为本地知识提示；网页抓取失败时跳过该页。
    """
    topic = state["topic"]
    logger.info(f"[搜索Agent] 搜索: {topic}")

    try:
        # Step 1: 搜索（已内置重试+降级）
        results = await search_web(topic, max_results=5)

        # Step 2: 并行抓取 Top 3 网页内容（每个 fetch 已内置重试+降级）
        top_urls = [r["url"] for r in results[:3] if r.get("url")]
        sources = []
        if top_urls:
            pages = await asyncio.gather(
                *[fetch_page(url) for url in top_urls],
                return_exceptions=True,
            )
            for i, page in enumerate(pages):
                if isinstance(page, Exception):
                    logger.warning(f"抓取异常 {top_urls[i]}: {page}")
                elif page:
                    sources.append({
                        "url": top_urls[i],
                        "title": results[i].get("title", ""),
                        "content": page,
                    })

        success_rate = f"{len(sources)}/{len(top_urls)}" if top_urls else "0/0"
        logger.info(f"[搜索Agent] 完成: 搜索{len(results)}条, 抓取{success_rate}页")

        # 标记降级状态供前端展示
        degraded = "降级" in results[0]["title"] if results else False

        return {
            "search_results": results,
            "sources": sources,
            "error": "搜索服务降级，使用本地知识库" if degraded else None,
        }
    except Exception as e:
        logger.error(f"[搜索Agent] 致命失败: {e}")
        return {"error": f"搜索失败: {e}", "search_results": [], "sources": []}
