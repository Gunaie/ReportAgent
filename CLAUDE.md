# CLAUDE.md — ReportAgent 项目上下文

## 项目概述

智能研究助手 — AI 驱动的对话式研究工具。输入任意研究主题，AI 自动 Web 搜索 → 多 Agent 并行分析（趋势/竞争/风险）→ 生成含引用的深度研究报告。对话式交互，SSE 实时反馈。

## 技术栈

| 层 | 技术 |
|----|------|
| 语言 | Python 3.12+ |
| 包管理 | uv |
| Agent | LangGraph |
| LLM | LangChain + langchain-openai (deepseek-v4-flash/v4-pro) |
| 搜索 | Tavily Search API + httpx |
| Web | FastAPI + SSE + Vanilla JS |
| 模板 | Jinja2 |
| 数据库 | SQLAlchemy async + aiosqlite |
| 日志 | loguru |

## 常用命令

```bash
source .venv/Scripts/activate
export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
uv sync
uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8002
uv run python -m pytest tests/ -v
```

## 模块结构

```
src/
├── config.py              # Pydantic Settings
├── exceptions.py          # 统一异常体系
├── agents/                # LangGraph 多Agent
│   ├── state.py           # ResearchState
│   ├── graph.py           # search → [trend ‖ competition ‖ risk] → synthesis
│   ├── search_agent.py    # Tavily搜索 + 网页抓取
│   ├── trend_agent.py     # 行业趋势 (flash)
│   ├── competition_agent.py     # 竞争格局 (pro)
│   ├── risk_research_agent.py   # 风险分析 (flash)
│   └── synthesis_research_agent.py  # 综合汇总 (pro)
├── tools/
│   └── web_search.py      # Tavily API + httpx 抓取
├── api/                   # FastAPI + SSE
│   ├── app.py, routes.py, sse.py, tasks.py, middleware.py
│   └── static/            # index.html + app.js
├── generator/             # Jinja2 报告渲染
│   ├── renderer.py
│   └── templates/research_report.md.j2
├── models/report.py       # Pydantic 模型
├── db/                    # SQLAlchemy async
│   └── engine.py, models.py, crud.py
└── utils/
    ├── logger.py          # loguru
    ├── model_router.py    # v4-flash/v4-pro 路由
    └── helpers.py         # 共享工具
```

## 环境变量 (.env)

```
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
TAVILY_API_KEY=tvly-xxx
DATABASE_URL=sqlite+aiosqlite:///./data/reports.db
OUTPUT_DIR=./outputs
```

## Agent 工作流

```
用户输入研究主题
  ↓
search_agent: 搜索 + 抓取网页
  ↓ (并行)
trend_agent + competition_agent + risk_agent
  ↓
synthesis_research_agent: 汇总报告
  ↓
Markdown → 浏览器渲染
```
