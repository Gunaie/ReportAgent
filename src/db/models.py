"""ORM 模型 — SQLAlchemy 映射到 SQLite 表。"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类。"""
    pass


class Report(Base):
    """研报记录表 — 对应每次生成的研报。"""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True, comment="任务UUID")
    topic = Column(String(200), nullable=False, index=True, comment="研究主题")
    stock_name = Column(String(50), nullable=False, default="", comment="股票简称")
    report_type = Column(String(20), nullable=False, default="single", comment="single|comparison")
    rating = Column(String(10), nullable=True, comment="综合评级")
    summary = Column(Text, nullable=True, comment="投资摘要")
    content_md = Column(Text, nullable=True, comment="Markdown原文")
    charts_json = Column(Text, nullable=True, comment="图表路径JSON数组")
    format = Column(String(10), nullable=False, default="md", comment="输出格式 md|html|pdf")
    file_path = Column(String(500), nullable=True, comment="最终文件路径")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, topic={self.topic}, rating={self.rating})>"


class WatchlistItem(Base):
    """自选股表。"""

    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), unique=True, nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(50), nullable=False, default="", comment="股票简称")
    notes = Column(Text, nullable=True, comment="备注")
    added_at = Column(DateTime, default=datetime.now, comment="添加时间")

    def __repr__(self) -> str:
        return f"<WatchlistItem(stock={self.stock_code}, name={self.stock_name})>"
