"""报告渲染器 — 基于 Jinja2 将分析内容组装为完整报告。"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from loguru import logger

from src.config import settings


# 模板目录
_TEMPLATE_DIR = Path(__file__).parent / "templates"


class ReportRenderer:
    """Jinja2 报告渲染引擎。"""

    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_single(self, state: dict) -> str:
        """渲染研究报告。

        Args:
            state: ResearchState 完成后的状态

        Returns:
            完整 Markdown 报告字符串
        """
        template = self.env.get_template("research_report.md.j2")
        md_content = template.render(
            topic=state.get("topic", ""),
            synthesis_analysis=state.get("synthesis_analysis", ""),
            trend_analysis=state.get("trend_analysis", ""),
            competition_analysis=state.get("competition_analysis", ""),
            risk_analysis=state.get("risk_analysis", ""),
            sources=state.get("sources", []),
        )
        return md_content.strip()

    def save_markdown(
        self, content: str, filename: str, output_dir: Path | None = None
    ) -> str:
        """保存 Markdown 到文件。"""
        if output_dir is None:
            output_dir = settings.output_md_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # 清理文件名
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:50]
        filepath = output_dir / f"{safe_name}_report.md"
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Markdown 报告已保存: {filepath}")
        return str(filepath)
