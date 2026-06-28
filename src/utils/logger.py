"""日志配置 — 基于 loguru，统一格式。"""

import sys
from loguru import logger


def setup_logger(level: str = "INFO") -> None:
    """初始化日志，输出到 stderr + 文件。"""
    logger.remove()  # 移除默认 handler

    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}:{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=level,
        colorize=True,
    )

    logger.add(
        "logs/report_agent_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        encoding="utf-8",
    )

    logger.info("日志系统初始化完成")
