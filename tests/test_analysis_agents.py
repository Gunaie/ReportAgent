"""分析 Agent 测试 — 趋势/竞争/风险 的输入输出和容错。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.state import ResearchState


# ====== 趋势 Agent ======

class TestTrendAgent:
    """趋势分析 Agent — 正常/空源/LLM失败。"""

    @pytest.fixture
    def state_with_sources(self, sample_topic, sample_sources):
        state = ResearchState(topic=sample_topic)
        state["sources"] = sample_sources
        return state

    @pytest.fixture
    def state_empty_sources(self, sample_topic):
        state = ResearchState(topic=sample_topic)
        state["sources"] = []
        return state

    @pytest.mark.asyncio
    async def test_normal_output_structure(self, state_with_sources):
        """正常流程 → 返回 trend_analysis Markdown。"""
        from src.agents.trend_agent import trend_agent

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
            content="## 行业趋势分析\n\n### 关键趋势\n1. **增长迅猛**: 行业年增长率超过30%，市场持续扩大\n2. **政策利好**: 多项支持政策出台"
        ))

        with patch("src.agents.trend_agent.create_llm", return_value=mock_llm):
            result = await trend_agent(state_with_sources)

        assert "trend_analysis" in result
        assert "关键趋势" in result["trend_analysis"]
        assert len(result["trend_analysis"]) > 30

    @pytest.mark.asyncio
    async def test_empty_sources_returns_placeholder(self, state_empty_sources):
        """无搜索来源 → 返回占位提示，不调 LLM。"""
        from src.agents.trend_agent import trend_agent

        with patch("src.agents.trend_agent.create_llm") as mock_create:
            result = await trend_agent(state_empty_sources)
            mock_create.assert_not_called()

        assert "trend_analysis" in result
        assert "暂无足够的搜索材料" in result["trend_analysis"]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error_message(self, state_with_sources):
        """LLM 调用失败 → 返回错误信息，不抛异常。"""
        from src.agents.trend_agent import trend_agent

        with patch("src.agents.trend_agent.create_llm", side_effect=RuntimeError("API timeout")):
            result = await trend_agent(state_with_sources)

        assert "trend_analysis" in result
        # 降级消息：使用安全兜底文案
        assert "暂不可用" in result["trend_analysis"] or "降级" in result["trend_analysis"]


# ====== 竞争 Agent ======

class TestCompetitionAgent:
    """竞争分析 Agent — 正常/空源/LLM失败。"""

    @pytest.fixture
    def state_with_sources(self, sample_topic, sample_sources):
        state = ResearchState(topic=sample_topic)
        state["sources"] = sample_sources
        return state

    @pytest.mark.asyncio
    async def test_normal_output_structure(self, state_with_sources):
        """正常流程 → 返回 competition_analysis Markdown（含表格）。"""
        from src.agents.competition_agent import competition_agent

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
            content="## 竞争格局分析\n\n| 公司 | 份额 |\n|------|------|\n| A | 30% |"
        ))

        with patch("src.agents.competition_agent.create_llm", return_value=mock_llm):
            result = await competition_agent(state_with_sources)

        assert "competition_analysis" in result
        assert "竞争格局" in result["competition_analysis"]
        assert "|" in result["competition_analysis"]  # 含表格

    @pytest.mark.asyncio
    async def test_empty_sources_returns_placeholder(self, sample_topic):
        """无搜索来源 → 返回占位提示。"""
        from src.agents.competition_agent import competition_agent

        state = ResearchState(topic=sample_topic)
        state["sources"] = []

        with patch("src.agents.competition_agent.create_llm") as mock_create:
            result = await competition_agent(state)
            mock_create.assert_not_called()

        assert "暂无足够的搜索材料" in result["competition_analysis"]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error_message(self, state_with_sources):
        """LLM 调用失败 → 返回错误信息。"""
        from src.agents.competition_agent import competition_agent

        with patch("src.agents.competition_agent.create_llm", side_effect=RuntimeError("boom")):
            result = await competition_agent(state_with_sources)

        assert "暂不可用" in result["competition_analysis"] or "降级" in result["competition_analysis"]


# ====== 风险 Agent ======

class TestRiskAgent:
    """风险分析 Agent — 正常/空源/LLM失败。"""

    @pytest.fixture
    def state_with_sources(self, sample_topic, sample_sources):
        state = ResearchState(topic=sample_topic)
        state["sources"] = sample_sources
        return state

    @pytest.mark.asyncio
    async def test_normal_output_structure(self, state_with_sources):
        """正常流程 → 返回 risk_analysis Markdown。"""
        from src.agents.risk_research_agent import risk_research_agent

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
            content="## 风险分析\n\n### 主要风险因素\n1. 产能过剩"
        ))

        with patch("src.agents.risk_research_agent.create_llm", return_value=mock_llm):
            result = await risk_research_agent(state_with_sources)

        assert "risk_analysis" in result
        assert "风险" in result["risk_analysis"]

    @pytest.mark.asyncio
    async def test_empty_sources_returns_placeholder(self, sample_topic):
        """无搜索来源 → 返回占位提示。"""
        from src.agents.risk_research_agent import risk_research_agent

        state = ResearchState(topic=sample_topic)
        state["sources"] = []

        with patch("src.agents.risk_research_agent.create_llm") as mock_create:
            result = await risk_research_agent(state)
            mock_create.assert_not_called()

        assert "暂无足够的搜索材料" in result["risk_analysis"]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error_message(self, state_with_sources):
        """LLM 调用失败 → 返回错误信息。"""
        from src.agents.risk_research_agent import risk_research_agent

        with patch("src.agents.risk_research_agent.create_llm", side_effect=RuntimeError("timeout")):
            result = await risk_research_agent(state_with_sources)

        assert "暂不可用" in result["risk_analysis"] or "降级" in result["risk_analysis"]


# ====== 综合 Agent ======

class TestSynthesisAgent:
    """综合汇总 Agent — 正常/上游全部失败/LLM失败。"""

    @pytest.fixture
    def state_all_good(self, sample_topic, sample_analyses, sample_sources):
        state = ResearchState(topic=sample_topic)
        state["sources"] = sample_sources
        state.update(sample_analyses)
        return state

    @pytest.fixture
    def state_all_failed(self, sample_topic):
        state = ResearchState(topic=sample_topic)
        state["trend_analysis"] = "## 行业趋势分析\n\n分析失败: API timeout"
        state["competition_analysis"] = "## 竞争格局分析\n\n分析失败: API timeout"
        state["risk_analysis"] = "## 风险分析\n\n分析失败: API timeout"
        return state

    @pytest.mark.asyncio
    async def test_normal_synthesis(self, state_all_good):
        """正常流程 → 生成完整报告。"""
        from src.agents.synthesis_research_agent import synthesis_research_agent

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
            content="## 摘要\n新能源汽车行业持续增长\n\n## 行业趋势\n..."
        ))

        with patch("src.agents.synthesis_research_agent.create_llm", return_value=mock_llm):
            result = await synthesis_research_agent(state_all_good)

        assert "final_report" in result
        assert "synthesis_analysis" in result
        assert "研究报告" in result["final_report"]
        assert len(result["final_report"]) > 100

    @pytest.mark.asyncio
    async def test_all_upstream_failed_skips_llm(self, state_all_failed):
        """上游三个分析全部失败 → 跳过 LLM，直接生成错误报告。"""
        from src.agents.synthesis_research_agent import synthesis_research_agent

        with patch("src.agents.synthesis_research_agent.create_llm") as mock_create:
            result = await synthesis_research_agent(state_all_failed)
            mock_create.assert_not_called()  # 不应调用 LLM

        assert "final_report" in result
        assert "失败" in result["final_report"]
        assert "上游分析" in result["final_report"] or "全部失败" in result["final_report"]

    @pytest.mark.asyncio
    async def test_llm_failure_generates_error_report(self, state_all_good):
        """LLM 调用失败 → 生成错误报告。"""
        from src.agents.synthesis_research_agent import synthesis_research_agent

        with patch("src.agents.synthesis_research_agent.create_llm", side_effect=RuntimeError("LLM crash")):
            result = await synthesis_research_agent(state_all_good)

        assert "final_report" in result
        assert "失败" in result["final_report"]
        assert "synthesis_analysis" in result
        assert "失败" in result["synthesis_analysis"]
