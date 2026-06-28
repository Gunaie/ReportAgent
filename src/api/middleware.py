"""FastAPI 中间件 — 请求日志、限流、异常处理。"""

import time
from collections import defaultdict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from src.exceptions import APIError, ReportAgentError


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 — 记录每个请求的 method/path/耗时/状态码。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} ({elapsed_ms:.1f}ms)"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简易内存限流中间件。

    按客户端 IP 限制请求频率。
    仅对 POST /api/research 等写操作限流。
    """

    RATE_LIMIT_PATHS = {"/api/research"}

    def __init__(self, app, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path not in self.RATE_LIMIT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        # 清理过期记录
        self._clients[client_ip] = [
            t for t in self._clients[client_ip] if t > window_start
        ]

        if len(self._clients[client_ip]) >= self.max_requests:
            logger.warning(f"限流触发: {client_ip} → {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
            )

        self._clients[client_ip].append(now)
        return await call_next(request)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常处理中间件 — 将 ReportAgentError 映射为 HTTP 状态码。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except APIError as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": str(e), "context": e.context},
            )
        except ReportAgentError as e:
            return JSONResponse(
                status_code=500,
                content={"detail": str(e), "context": e.context},
            )
        except Exception:
            logger.exception(f"未处理异常: {request.method} {request.url.path}")
            return JSONResponse(
                status_code=500,
                content={"detail": "服务器内部错误"},
            )
