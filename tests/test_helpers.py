"""工具函数测试 — format_sources / extract_rating / extract_summary。"""

import pytest
from src.utils.helpers import (
    format_sources,
    extract_rating,
    extract_summary,
    safe_float,
    to_float,
    validate_stock_code,
)


class TestFormatSources:
    """来源格式化 — Agent 输入预处理。"""

    def test_formats_multiple_sources(self, sample_sources):
        """多个来源 → 格式化文本含来源编号。"""
        text = format_sources(sample_sources)

        assert "来源1:" in text
        assert "来源2:" in text
        assert "来源3:" in text
        for s in sample_sources:
            assert s["title"] in text
            assert s["url"] in text

    def test_empty_list_returns_empty_string(self):
        """空列表 → 返回空字符串。"""
        assert format_sources([]) == ""

    def test_truncates_long_content(self):
        """超长内容被截断。"""
        sources = [{"title": "T", "url": "U", "content": "x" * 5000}]
        text = format_sources(sources, max_content_len=100)
        assert len(text) < 500  # 远小于原始 5000

    def test_missing_fields_handled(self):
        """缺少字段不崩溃。"""
        sources = [{}]
        text = format_sources(sources)
        assert "无标题" in text


class TestExtractRating:
    """评级提取。"""

    def test_extracts_buy(self):
        assert extract_rating("综合评级: **买入**") == "买入"

    def test_extracts_neutral(self):
        assert extract_rating("建议中性，观望") == "中性"

    def test_no_match_returns_default(self):
        assert extract_rating("暂无明确结论") == "未评级"

    def test_empty_text(self):
        assert extract_rating("") == "未评级"


class TestExtractSummary:
    """摘要提取。"""

    def test_extracts_first_meaningful_line(self):
        text = "# 标题\n\n这是一段超过20个字符的有效摘要内容"
        result = extract_summary(text, max_len=50)
        assert "有效摘要" in result
        assert len(result) <= 50

    def test_empty_text(self):
        assert extract_summary("") == ""


class TestSafeFloat:
    """安全数值转换。"""

    def test_normal_float(self):
        assert safe_float("3.14") == 3.14

    def test_none_returns_zero(self):
        assert safe_float(None) == 0.0

    def test_dash_returns_zero(self):
        assert safe_float("--") == 0.0

    def test_comma_handled(self):
        assert safe_float("1,234.56") == 1234.56


class TestToFloat:
    """带单位转换的数值。"""

    def test_percent_unit(self):
        assert to_float("91.5%", "%") == 91.5

    def test_yuan_to_yi(self):
        assert to_float("150000000000", "元") == 1500.0

    def test_auto_large_number(self):
        assert to_float("1e10", "auto") < 1e10  # >1e9 会除以 1e8


class TestValidateStockCode:
    """股票代码校验。"""

    def test_valid_sh_code(self):
        assert validate_stock_code("600519") is True

    def test_valid_sz_code(self):
        assert validate_stock_code("000858") is True

    def test_invalid_short(self):
        assert validate_stock_code("123") is False

    def test_invalid_chars(self):
        assert validate_stock_code("abc123") is False
