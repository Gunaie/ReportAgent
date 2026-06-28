# ReportAgent Docker 镜像
# 多阶段构建: builder → runtime

# ====== Stage 1: Builder ======
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装系统依赖 (weasyprint 需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 设置 uv 环境
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_LINK_MODE=copy

# 先只复制依赖相关文件，利用 Docker 缓存
COPY pyproject.toml uv.lock ./

# 安装依赖到虚拟环境
RUN uv sync --frozen --no-dev

# ====== Stage 2: Runtime ======
FROM python:3.12-slim AS runtime

WORKDIR /app

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    fonts-simhei \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制源码
COPY src/ ./src/
COPY pyproject.toml ./

# 创建运行时目录
RUN mkdir -p /app/data /app/logs /app/outputs

# 使用虚拟环境中的 Python
ENV PATH="/app/.venv/bin:$PATH"

# 非 root 用户运行
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')" || exit 1

EXPOSE 8002

CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8002"]
