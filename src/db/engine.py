"""数据库引擎 — SQLAlchemy async engine + session 管理。"""

from pathlib import Path
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from loguru import logger

from src.config import settings

_engine = None
_session_factory = None


def get_engine():
    """获取全局异步引擎（延迟初始化）。"""
    global _engine, _session_factory
    if _engine is None:
        db_url = settings.database_url
        # 确保 data/ 目录存在
        if "sqlite" in db_url:
            # 从 URL 中提取路径: sqlite+aiosqlite:///./data/reports.db
            db_path = db_url.split(":///")[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
        )
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info(f"数据库引擎已初始化: {db_url}")
    return _engine


async def init_db() -> None:
    """创建所有表（首次启动调用）。"""
    from src.db.models import Base
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表已创建/验证")


async def get_session() -> AsyncSession:
    """获取一个新的异步 session。

    调用方负责 close()。
    推荐使用 `async with session:` 上下文管理器。
    """
    global _session_factory
    if _session_factory is None:
        get_engine()  # 确保已初始化
    return _session_factory()
