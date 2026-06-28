"""FastAPI 应用工厂 — 组装路由、SSE、中间件、静态文件。"""

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.api.routes import router as api_router
from src.api.sse import router as sse_router
from src.api.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    ExceptionHandlerMiddleware,
)
from src.db.engine import init_db, get_engine
from src.utils.logger import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 — 启动/关闭钩子。"""
    # 启动
    setup_logger()
    await init_db()
    logger.info("FastAPI 应用已启动")
    yield
    # 关闭
    engine = get_engine()
    await engine.dispose()
    logger.info("FastAPI 应用已关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。

    Returns:
        配置完成的 FastAPI 实例
    """
    app = FastAPI(
        title="智能研报生成助手",
        description="A股AI深度研报自动生成服务 — 输入股票代码，一键生成专业研报",
        version="0.1.0",
        lifespan=lifespan,
    )

    # === 中间件（顺序有讲究：异常 → 日志 → 限流 → CORS） ===
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=10,
        window_seconds=60,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # === 路由 ===
    app.include_router(api_router)
    app.include_router(sse_router)

    # === 健康检查 ===
    @app.get("/health", tags=["system"])
    async def health_check():
        """服务健康检查 — 用于 K8s liveness/readiness probe。"""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "service": "report-agent",
        }

    # === 报告文件静态服务 ===
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

    # === 静态文件（前端，必须在最后） ===
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    logger.info("FastAPI 应用已创建")
    return app


# 模块级 app 实例（uvicorn 入口用）
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8002, reload=True)
