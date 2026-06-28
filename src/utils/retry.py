"""重试与降级 — 指数退避 + 优雅降级，确保外部依赖故障不阻塞核心流程。"""

import asyncio
import functools
from typing import Callable, Awaitable
from loguru import logger


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 15.0,
    exceptions: tuple = (Exception,),
    on_retry: Callable | None = None,
):
    """异步重试装饰器 — 指数退避。

    Args:
        max_attempts: 最多尝试次数（含首次）
        base_delay: 首次重试延迟秒数
        max_delay: 最大延迟上限
        exceptions: 触发重试的异常类型
        on_retry: 每次重试前的回调(attempt, exception)

    Usage:
        @retry_async(max_attempts=3, base_delay=1.0)
        async def call_api(): ...
    """

    def decorator(func: Callable[..., Awaitable]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts:
                        logger.error(
                            f"[重试耗尽] {func.__name__} "
                            f"失败 {max_attempts}/{max_attempts}: {e}"
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        f"[重试] {func.__name__} "
                        f"失败 {attempt}/{max_attempts}, "
                        f"{delay:.1f}s 后重试: {e}"
                    )
                    if on_retry:
                        on_retry(attempt, e)
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore

        return wrapper

    return decorator


async def safe_call(
    coro_factory: Callable[[], Awaitable],
    fallback,
    name: str = "unknown",
    max_attempts: int = 2,
    base_delay: float = 0.5,
):
    """安全调用 — 带重试 + 降级兜底。

    Args:
        coro_factory: 异步调用工厂函数
        fallback: 失败时返回的默认值
        name: 调用名称（用于日志）
        max_attempts: 重试次数
        base_delay: 重试延迟

    Returns:
        调用成功的结果，或降级兜底值
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_factory()
        except Exception as e:
            if attempt == max_attempts:
                logger.error(f"[降级] {name} 最终失败，启用兜底: {e}")
                return fallback() if callable(fallback) else fallback
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(f"[重试] {name} 失败 {attempt}/{max_attempts}: {e}")
            await asyncio.sleep(delay)
    return fallback() if callable(fallback) else fallback


class DegradationTracker:
    """降级状态追踪 — 记录外部依赖的健康状况。"""

    def __init__(self):
        self._failures: dict[str, int] = {}
        self._degraded: set[str] = set()

    def record_failure(self, service: str):
        self._failures[service] = self._failures.get(service, 0) + 1
        if self._failures[service] >= 3:
            self._degraded.add(service)

    def record_success(self, service: str):
        self._failures[service] = 0
        self._degraded.discard(service)

    def is_degraded(self, service: str) -> bool:
        return service in self._degraded

    @property
    def health_report(self) -> dict:
        return {
            "failures": dict(self._failures),
            "degraded": list(self._degraded),
        }


# 全局追踪器
degradation = DegradationTracker()
