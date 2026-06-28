"""搜索 Agent 容错测试 — 空结果/抓取失败/异常兜底。"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.agents.state import ResearchState


class TestSearchAgent:
    """搜索 Agent — 正常 + 异常路径。"""

    @pytest.fixture
    def state(self):
        return ResearchState(topic="测试主题")

    @pytest.mark.asyncio
    async def test_no_results_returns_empty_sources(self, state):
        """搜索无结果 → 返回空 sources。"""
        from src.agents.search_agent import search_agent

        with patch("src.agents.search_agent.search_web", new=AsyncMock(return_value=[])):
            result = await search_agent(state)

        assert "sources" in result
        assert result["sources"] == []
        assert "search_results" in result
        assert result["search_results"] == []

    @pytest.mark.asyncio
    async def test_fetch_failures_gracefully_skipped(self, state):
        """部分抓取失败 → 跳过失败项，保留成功的。"""
        from src.agents.search_agent import search_agent

        mock_results = [
            {"title": "Good", "url": "https://ok.com", "content": "OK"},
            {"title": "Bad", "url": "https://fail.com", "content": "Bad"},
        ]
        mock_fetch = AsyncMock(side_effect=["page content 1", Exception("network error")])

        with patch("src.agents.search_agent.search_web", new=AsyncMock(return_value=mock_results)):
            with patch("src.agents.search_agent.fetch_page", new=mock_fetch):
                result = await search_agent(state)

        assert len(result["sources"]) == 1
        assert result["sources"][0]["title"] == "Good"
        assert result["sources"][0]["content"] == "page content 1"

    @pytest.mark.asyncio
    async def test_search_exception_returns_error(self, state):
        """搜索抛异常 → 返回 error 字段。"""
        from src.agents.search_agent import search_agent

        with patch("src.agents.search_agent.search_web", side_effect=RuntimeError("boom")):
            result = await search_agent(state)

        assert "error" in result
        assert "boom" in result["error"]
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_fetch_all_fail_returns_empty_sources(self, state):
        """全部抓取失败 → sources 为空但不报 error。"""
        from src.agents.search_agent import search_agent

        mock_results = [
            {"title": "Fail1", "url": "https://fail1.com"},
            {"title": "Fail2", "url": "https://fail2.com"},
        ]
        mock_fetch = AsyncMock(side_effect=[Exception("e1"), Exception("e2")])

        with patch("src.agents.search_agent.search_web", new=AsyncMock(return_value=mock_results)):
            with patch("src.agents.search_agent.fetch_page", new=mock_fetch):
                result = await search_agent(state)

        assert result["sources"] == []
        assert "error" not in result  # 抓取失败不阻塞流程

    @pytest.mark.asyncio
    async def test_search_results_included_in_return(self, state):
        """search_results 包含在返回值中（非 state 突变）。"""
        from src.agents.search_agent import search_agent

        mock_results = [
            {"title": "R1", "url": "https://r1.com", "content": "C1"},
        ]

        with patch("src.agents.search_agent.search_web", new=AsyncMock(return_value=mock_results)):
            with patch("src.agents.search_agent.fetch_page", new=AsyncMock(return_value="")):
                result = await search_agent(state)

        assert "search_results" in result
        assert len(result["search_results"]) == 1
        assert result["search_results"][0]["title"] == "R1"
