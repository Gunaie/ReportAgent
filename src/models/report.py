"""研报结构 — 输出报告的完整数据模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


Rating = Literal["买入", "增持", "中性", "减持", "卖出"]
RiskLevel = Literal["低", "中", "高"]
OutputFormat = Literal["md", "html", "pdf"]
ReportType = Literal["single", "comparison"]
ChartType = Literal["trend", "radar", "bar"]


class ChartInfo(BaseModel):
    """图表元数据。"""

    title: str = Field(..., description="图表标题")
    chart_type: ChartType = Field(..., description="图表类型: trend/radar/bar")
    file_path: str = Field(..., description="图表文件相对路径")
    width: int = Field(default=800, description="图片宽度（px）")
    height: int = Field(default=400, description="图片高度（px）")


class ReportSection(BaseModel):
    """研报单个章节。"""

    title: str = Field(..., description="章节标题")
    content: str = Field(default="", description="章节正文（Markdown）")
    chart: ChartInfo | None = Field(default=None, description="关联图表")
    subsections: list[ReportSection] = Field(default_factory=list, description="子章节")


class AnalysisResult(BaseModel):
    """单股分析完整结果 — 对应一次分析任务的输出。"""

    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票简称")
    rating: Rating = Field(default="中性", description="综合评级")
    target_price: float | None = Field(default=None, description="目标价（元）")
    risk_level: RiskLevel = Field(default="中", description="风险等级")
    summary: str = Field(default="", description="一句话摘要")
    sections: list[ReportSection] = Field(default_factory=list, description="报告章节列表")
    charts: list[ChartInfo] = Field(default_factory=list, description="图表清单")
    generated_at: datetime | None = Field(default=None, description="生成时间（工作流结束时赋值）")


class ComparisonResult(BaseModel):
    """多股对比分析结果。"""

    report_type: ReportType = Field(default="comparison", description="报告类型")
    stocks: list[AnalysisResult] = Field(default_factory=list, description="各股分析结果")
    comparison_sections: list[ReportSection] = Field(default_factory=list, description="对比分析章节")
    ranking: list[dict] = Field(default_factory=list, description="综合排名 [{code, score, rank}]")
    generated_at: datetime | None = Field(default=None, description="生成时间（工作流结束时赋值）")


class ReportMeta(BaseModel):
    """报告持久化元数据 — 对应数据库 reports 表。"""

    id: int | None = Field(default=None, description="数据库主键")
    task_id: str = Field(..., description="任务 UUID")
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票简称")
    report_type: ReportType = Field(default="single", description="single | comparison")
    rating: str | None = Field(default=None, description="评级")
    summary: str | None = Field(default=None, description="摘要")
    format: OutputFormat = Field(default="md", description="输出格式")
    file_path: str | None = Field(default=None, description="文件路径")
    created_at: datetime | None = Field(default=None, description="创建时间")
