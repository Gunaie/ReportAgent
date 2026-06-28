"""数据持久层 — SQLAlchemy async + aiosqlite。

提供异步数据库引擎、ORM 模型和 CRUD 操作。
SQLite 单文件数据库，零外部依赖。
"""

from src.db.engine import get_engine, init_db, get_session
from src.db.models import Report, WatchlistItem
from src.db.crud import ReportCRUD, WatchlistCRUD

__all__ = [
    "get_engine",
    "init_db",
    "get_session",
    "Report",
    "WatchlistItem",
    "ReportCRUD",
    "WatchlistCRUD",
]
