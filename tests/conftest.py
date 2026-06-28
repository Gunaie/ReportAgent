"""pytest 全局配置和共享 fixtures — 研究助手项目。"""

import os
import sys
from pathlib import Path

import pytest

# 确保 src/ 在 import path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

# 设置测试环境变量（覆盖 .env）
os.environ.setdefault("DASHSCOPE_API_KEY", "sk-test-mock-key")
os.environ.setdefault("DASHSCOPE_BASE_URL", "https://api.example.com/v1")
os.environ.setdefault("TAVILY_API_KEY", "tvly-test-mock-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test_reports.db")
os.environ.setdefault("OUTPUT_DIR", "./outputs/test")


# ====== 研究主题 Fixtures ======


@pytest.fixture
def sample_topic() -> str:
    """示例研究主题。"""
    return "新能源汽车行业发展趋势"


@pytest.fixture
def sample_search_results() -> list[dict]:
    """示例搜索结果。"""
    return [
        {"title": "新能源汽车2025年市场报告", "url": "https://example.com/ev-2025", "content": "新能源汽车市场持续增长..."},
        {"title": "动力电池技术突破", "url": "https://example.com/battery", "content": "固态电池技术取得重大进展..."},
        {"title": "政策支持新能源汽车发展", "url": "https://example.com/policy", "content": "多地出台新能源补贴政策..."},
    ]


@pytest.fixture
def sample_sources() -> list[dict]:
    """示例抓取的网页来源。"""
    return [
        {
            "url": "https://example.com/ev-2025",
            "title": "新能源汽车2025年市场报告",
            "content": "2025年新能源汽车渗透率突破50%，市场规模达到1.2万亿元。主要玩家包括比亚迪、特斯拉、蔚来等。",
        },
        {
            "url": "https://example.com/battery",
            "title": "动力电池技术突破",
            "content": "宁德时代发布第三代固态电池，能量密度提升40%。充电速度从30分钟缩短至15分钟。",
        },
        {
            "url": "https://example.com/policy",
            "title": "政策支持新能源汽车发展",
            "content": "工信部发布《新能源汽车产业发展规划（2025-2030）》，提出到2030年新能源汽车销量占比达60%。",
        },
    ]


@pytest.fixture
def sample_analyses() -> dict:
    """示例三份分析结果。"""
    return {
        "trend_analysis": "## 行业趋势分析\n\n### 关键趋势\n1. 渗透率加速提升\n2. 智能化竞争加剧\n\n### 行业阶段判断\n行业处于快速上升期",
        "competition_analysis": "## 竞争格局分析\n\n### 竞争格局概览\n- 主要参与者: 比亚迪、特斯拉、蔚来、小鹏\n- 市场集中度: 中等偏高\n\n### 头部公司对比\n| 公司 | 份额 | 优势 |\n|------|------|------|\n| 比亚迪 | 35% | 垂直整合 |\n| 特斯拉 | 15% | 品牌溢价 |",
        "risk_analysis": "## 风险分析\n\n### 主要风险因素\n1. **产能过剩（中期）**: 行业扩产过快\n2. **原材料波动（短期）**: 锂价波动\n\n### 风险评级\n- 整体风险水平: 中",
    }


# ====== ResearchState Fixture ======


@pytest.fixture
def sample_research_state(sample_topic, sample_search_results, sample_sources, sample_analyses):
    """构造一个包含完整数据的 ResearchState。"""
    from src.agents.state import ResearchState

    state = ResearchState(topic=sample_topic)
    state["search_results"] = sample_search_results
    state["sources"] = sample_sources
    state.update(sample_analyses)
    return state


# ====== Helpers Fixtures ======


@pytest.fixture
def sample_report_markdown(sample_topic, sample_analyses) -> str:
    """示例报告 Markdown 文本。"""
    return f"""# 研究报告: {sample_topic}

> 生成时间: 测试 | 免责声明: 本报告由AI自动生成

---

## 摘要
新能源汽车行业持续快速增长，渗透率提升至50%以上。

## 行业趋势
{sample_analyses['trend_analysis']}

## 竞争格局
{sample_analyses['competition_analysis']}

## 风险提示
{sample_analyses['risk_analysis']}

---

*本报告仅供研究参考*
"""
