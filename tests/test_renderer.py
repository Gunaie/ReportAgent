"""报告渲染测试 — Jinja2 模板 + 文件保存。"""

import pytest
import tempfile
from pathlib import Path
from src.generator.renderer import ReportRenderer


class TestReportRenderer:
    """Jinja2 渲染引擎 — 模板渲染 + 文件输出。"""

    def test_render_single_produces_markdown(self, sample_research_state):
        """渲染 ResearchState → 生成完整 Markdown。"""
        renderer = ReportRenderer()
        md = renderer.render_single(sample_research_state)

        assert len(md) > 50
        assert "# 研究报告:" in md
        assert sample_research_state["topic"] in md
        assert "免责声明" in md or "参考" in md

    def test_render_includes_synthesis(self, sample_research_state):
        """渲染结果包含 synthesis_analysis 内容。"""
        sample_research_state["synthesis_analysis"] = "## 核心发现\n\n测试摘要内容"
        renderer = ReportRenderer()
        md = renderer.render_single(sample_research_state)

        assert "核心发现" in md
        assert "测试摘要内容" in md

    def test_render_lists_sources(self, sample_research_state, sample_sources):
        """渲染结果包含引用来源链接。"""
        renderer = ReportRenderer()
        md = renderer.render_single(sample_research_state)

        for s in sample_sources:
            assert s["url"] in md

    def test_render_empty_state_does_not_crash(self):
        """空状态渲染不崩溃。"""
        from src.agents.state import ResearchState

        state = ResearchState(topic="empty")
        renderer = ReportRenderer()
        md = renderer.render_single(state)

        assert len(md) > 0
        assert "研究报告" in md

    def test_save_markdown_writes_file(self):
        """save_markdown 写入文件并返回路径。"""
        renderer = ReportRenderer()
        content = "# Test Report\n\nHello World"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.save_markdown(content, "test_topic", output_dir=Path(tmpdir))
            saved = Path(path)

            assert saved.exists()
            assert saved.read_text(encoding="utf-8") == content
            assert saved.suffix == ".md"

    def test_save_markdown_sanitizes_filename(self):
        """文件名中的特殊字符被清理。"""
        renderer = ReportRenderer()
        content = "test"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.save_markdown(content, "特殊 字符!@# test", output_dir=Path(tmpdir))
            name = Path(path).stem

            # 不应含空格或特殊字符
            assert " " not in name
            assert "!" not in name
            assert "@" not in name
            assert "#" not in name
            assert "_report" in name
