# 📊 智能研究助手 (ReportAgent)

> AI 驱动的对话式研究工具 — 输入研究主题，自动搜索 + 多 Agent 并行分析 → 生成含引用的深度研究报告。

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138-009688)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-orange)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 为什么做这个项目

传统研究报告撰写有三个痛点：

1. **信息收集耗时** — 人工搜索、筛选、阅读网页需要数小时
2. **分析视角单一** — 个人很难同时覆盖趋势、竞争、风险三个维度
3. **格式不统一** — 每个人写的报告结构各异，缺少标准化

**ReportAgent** 解决这些问题：用户输入一个主题，AI 自动完成 Web 搜索 → 多角度并行分析 → 结构化报告输出，**3 分钟完成从提问到报告的全流程**。

核心思路：**澄清 → 搜索 → [趋势 ‖ 竞争 ‖ 风险] → 综合报告**。

---

## 技术选型理由

### 为什么 LangGraph？

| 对比方案 | 问题 | LangGraph 优势 |
|----------|------|----------------|
| 手动串行调用 | 趋势/竞争/风险依次执行，慢 | **fan-out → fan-in 并行**，3 个分析同时跑 |
| if-else 编排 | 状态传递靠变量，难维护 | **显式 StateGraph**，每个节点声明读写字段 |
| CrewAI/AutoGen | 黑盒调度、难调试 | **白盒工作流**，每个节点可单步调试 |

LangGraph 的 `StateGraph` 将研究流程建模为有向图：`clarify → search → [trend ‖ competition ‖ risk] → synthesis`，状态在节点间自动流转合并。

### 为什么 DeepSeek？

| 对比 | DeepSeek v4 | GPT-4o | Claude |
|------|-------------|--------|--------|
| 中文理解 | ⭐⭐⭐⭐⭐ 原生训练 | ⭐⭐⭐ | ⭐⭐⭐ |
| 推理成本 | 极低（DashScope） | 高 | 中 |
| 上下文窗口 | 1M tokens | 128K | 200K |
| 结构化输出 | 稳定 JSON | 偶尔格式错误 | 优秀但贵 |

DeepSeek v4-flash 处理简单任务（搜索摘要/澄清追问），v4-pro 处理深度推理（竞争分析/综合汇总），**路由分配节省约 60% 成本**。

### 为什么 Tavily？

| 对比 | Tavily | SerpAPI | 自建爬虫 |
|------|--------|---------|----------|
| AI 优化 | ✅ 原生为 LLM 设计 | ❌ 原始搜索结果 | ❌ 需自行清洗 |
| 内容摘要 | ✅ 自动提取正文 | ❌ 仅标题+链接 | ❌ 需自行解析 |
| 价格 | 免费额度 1000/月 | $50/月起 | 服务器成本 |

Tavily 返回 AI 友好的结构化结果（标题+URL+摘要），省去 HTML 清洗环节。

### 为什么 FastAPI + SSE？

- **FastAPI** — 原生 async、自动 OpenAPI 文档、类型安全
- **SSE** — 单向推送，比 WebSocket 更简单；研究进度天然是"服务端推送，客户端只读"
- **Jinja2** — Markdown 模板渲染，零前端框架依赖

---

## 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (Vanilla JS)                    │
│         对话气泡 UI  ←──SSE──→  进度条 / 报告渲染          │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP + SSE
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI 应用层                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ routes  │  │   SSE    │  │  middleware (限流/日志)│   │
│  └────┬────┘  └────┬─────┘  └──────────────────────┘   │
│       │            │                                     │
│  ┌────▼────────────▼─────┐                              │
│  │    TaskManager        │  ← DB 持久化任务状态           │
│  │  (create/update/get)  │                              │
│  └───────────┬───────────┘                              │
└──────────────┼──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                 LangGraph 工作流                          │
│                                                          │
│   ┌─────────┐     ┌─────────────────────────┐           │
│   │ clarify │────▶│        search           │           │
│   │ (澄清)  │     │  Tavily API + 网页抓取   │           │
│   └────┬────┘     └──────────┬──────────────┘           │
│        │ 追问                │ 并行 fan-out              │
│        ▼               ┌─────┼─────┐                    │
│       END          ┌────▼──┐┌───▼──┐┌───▼───┐          │
│                    │ trend ││compete││ risk  │          │
│                    │ v4-flash│v4-pro││v4-flash│         │
│                    └───┬───┘└──┬───┘└───┬───┘          │
│                        │ fan-in│       │                │
│                        └───────┼───────┘                │
│                           ┌────▼────┐                    │
│                           │synthesis│ (v4-pro)          │
│                           └────┬────┘                    │
│                                ▼                         │
│                           Markdown 报告                  │
└──────────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                    数据层                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐     │
│  │  Report  │  │   Task   │  │  Conversation     │     │
│  │ (研报)   │  │ (任务)   │  │  (对话历史)       │     │
│  └──────────┘  └──────────┘  └───────────────────┘     │
│              SQLAlchemy + SQLite / PostgreSQL           │
└──────────────────────────────────────────────────────────┘
```

### Agent 工作流详解

```
用户输入: "分析半导体行业"
    │
    ▼
┌─────────────────────────────┐
│ clarify_agent (v4-flash)    │  ← 判断需求是否明确
│ need_clarify=True           │
│ "你想侧重哪个细分领域？"     │
└─────────────┬───────────────┘
              │ 用户回复: "芯片制造技术趋势"
              ▼
┌─────────────────────────────┐
│ search_agent (Tavily)       │  ← Web 搜索 + 抓取 Top 3 网页
│ 5 results → fetch content   │
└─────────────┬───────────────┘
              │ 并行 fan-out
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐
│ trend │ │compet.│ │ risk  │    ← 三个分析 Agent 同时执行
│ 趋势  │ │ 竞争  │ │ 风险  │
└───┬───┘ └───┬───┘ └───┬───┘
    └─────────┼─────────┘
              ▼
┌─────────────────────────────┐
│ synthesis_agent (v4-pro)    │  ← 综合汇总 → Markdown 报告
│ 摘要 + 趋势 + 竞争 + 风险    │
└─────────────────────────────┘
```

---

## 快速开始

### 前提条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 包管理器
- Tavily API Key（[免费注册](https://tavily.com)）
- DashScope API Key（[阿里云百炼](https://dashscope.aliyun.com)）

### 1. 克隆项目

```bash
git clone https://github.com/Gunaie/ReportAgent.git
cd ReportAgent
```

### 2. 安装依赖

```bash
# 配置国内镜像（可选，加速下载）
export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

uv sync
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate     # Mac/Linux
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```ini
DASHSCOPE_API_KEY=sk-xxxxxxxx
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
TAVILY_API_KEY=tvly-xxxxxxxx
DATABASE_URL=sqlite+aiosqlite:///./data/reports.db
OUTPUT_DIR=./outputs
```

### 4. 启动

```bash
uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8002
```

打开浏览器访问 `http://localhost:8002`

### 5. 使用

1. 输入研究主题（如"分析新能源汽车动力电池技术趋势"）
2. AI 判断需求是否明确 — 模糊主题会追问澄清
3. 确认后自动搜索 → 分析 → 生成报告
4. 报告含摘要、趋势、竞争、风险、信息来源

---

## 项目结构

```
ReportAgent/
├── src/
│   ├── agents/               # LangGraph 多 Agent
│   │   ├── state.py          # ResearchState 共享状态
│   │   ├── graph.py          # 工作流编排 (fan-out/fan-in)
│   │   ├── clarify_agent.py  # 需求澄清 (v4-flash)
│   │   ├── search_agent.py   # Tavily 搜索 + 网页抓取
│   │   ├── trend_agent.py    # 行业趋势分析 (v4-flash)
│   │   ├── competition_agent.py  # 竞争格局分析 (v4-pro)
│   │   ├── risk_research_agent.py # 风险分析 (v4-flash)
│   │   └── synthesis_research_agent.py # 综合汇总 (v4-pro)
│   ├── api/                  # FastAPI + SSE
│   │   ├── app.py            # 应用工厂 + lifespan
│   │   ├── routes.py         # REST 路由
│   │   ├── sse.py            # SSE 实时推送
│   │   ├── tasks.py          # 任务管理 (DB 持久化)
│   │   ├── middleware.py     # 限流/日志/异常处理
│   │   └── static/           # 前端 (Vanilla JS)
│   ├── tools/
│   │   └── web_search.py     # Tavily API + httpx 抓取
│   ├── generator/
│   │   ├── renderer.py       # Jinja2 报告渲染
│   │   └── templates/        # Markdown 模板
│   ├── db/                   # SQLAlchemy async
│   │   ├── engine.py         # 引擎 + session 管理
│   │   ├── models.py         # ORM 模型 (Report/Task/Conversation)
│   │   └── crud.py           # CRUD 操作
│   ├── models/report.py      # Pydantic 数据模型
│   ├── utils/
│   │   ├── model_router.py   # v4-flash/v4-pro 路由
│   │   ├── helpers.py        # 共享工具函数
│   │   └── logger.py         # loguru 配置
│   ├── config.py             # Pydantic Settings
│   └── exceptions.py         # 统一异常体系
├── tests/                    # 测试
├── alembic/                  # 数据库迁移
├── .github/workflows/        # CI/CD
├── pyproject.toml
└── README.md
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/research` | 提交研究任务 |
| POST | `/api/research/continue` | 回复澄清问题 |
| GET | `/api/task/{task_id}` | 查询任务状态 |
| GET | `/api/conversation/{task_id}` | 获取对话历史 |
| GET | `/api/sse/{task_id}` | SSE 实时进度 |
| GET | `/api/reports` | 历史报告列表（分页） |
| GET | `/api/reports/{task_id}/content` | 报告 Markdown 全文 |
| GET | `/health` | 健康检查 |

---

## 模型路由策略

| Agent | 模型 | 理由 |
|-------|------|------|
| clarify | v4-flash | 简单判断，低延迟 |
| search | v4-flash | 搜索摘要，高吞吐 |
| trend | v4-flash | 趋势提炼，结构化输出 |
| competition | **v4-pro** | 深度对比推理，需强逻辑 |
| risk | v4-flash | 风险识别，模式匹配 |
| synthesis | **v4-pro** | 综合汇总，需长文生成质量 |

flash 负责 70% 的任务量，pro 负责 30% 的关键推理。

---

## 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 语言 | Python | 3.12+ |
| 包管理 | uv | latest |
| Agent 框架 | LangGraph | 1.2.x |
| LLM 接入 | LangChain + langchain-openai | 1.3.x |
| 模型 | DeepSeek v4-flash / v4-pro | — |
| 搜索 | Tavily Search API | — |
| Web 框架 | FastAPI + SSE | 0.138 |
| 模板 | Jinja2 | 3.1 |
| 数据库 | SQLAlchemy async + aiosqlite | 2.0 |
| 日志 | loguru | 0.7 |
| HTTP 客户端 | httpx | 0.28 |

---

## 效果截图

### 对话式交互
```
┌─────────────────────────────────────────┐
│  📊 智能研究助手                         │
│  对话式 AI 研究 — 多轮澄清 + 深度分析     │
├─────────────────────────────────────────┤
│                                         │
│  🤖 你好！输入你想研究的主题…            │
│                                         │
│                         👤 分析半导体行业 │
│                                         │
│  🤖 你想侧重分析半导体哪个细分领域？      │
│     是芯片设计、制造、设备还是材料？      │
│                                         │
│              👤 芯片制造，关注技术趋势    │
│                                         │
│  ┌─ 搜索中… [running] ───────── 25% ─┐  │
│                                         │
│  🤖 📄 研究报告                         │
│     ## 摘要                             │
│     全球芯片制造技术正经历…              │
│     ## 行业趋势                         │
│     1. 先进制程竞争加剧                  │
│     2. 第三代半导体材料突破              │
│     …                                   │
│     📚 参考来源: 5 条                    │
└─────────────────────────────────────────┘
```

### 生成的报告示例结构

```markdown
# 研究报告: 芯片制造技术趋势

> 生成时间: 2026-06-29 | AI 自动生成

---

## 摘要
全球芯片制造正从 5nm 向 3nm/2nm 演进，台积电、三星、英特尔三强格局…

## 行业趋势
### 关键趋势
1. **先进制程竞赛加速** — 台积电 2nm 预计 2025 年量产
2. **Chiplet 技术普及** — 降低先进封装门槛
3. **第三代半导体材料** — SiC/GaN 在功率器件渗透率提升

### 行业阶段判断
行业处于成熟扩张期，技术迭代速度保持高位

## 竞争格局
| 公司 | 份额 | 优势 | 劣势 |
|------|------|------|------|
| 台积电 | 58% | 先进制程领先 | 地缘风险 |
| 三星 | 16% | 全产业链 | 良率差距 |
| 英特尔 | 8% | IDM 2.0 战略 | 转型期 |

## 风险提示
1. **地缘政治风险（长期）** — 设备出口管制加剧
2. **产能过剩（中期）** — 成熟制程扩产过快

## 📚 参考来源
1. [全球半导体制造趋势报告](https://...)
2. [台积电2025技术路线图](https://...)
...
```

---

## 后续规划

- [ ] 可视化图表（Plotly 趋势图/雷达图/风险矩阵）
- [ ] 报告模板市场（新能源/半导体/医药/AI 等行业模板）
- [ ] 多格式导出（Markdown → PDF/Word/PPT via Pandoc）
- [ ] 搜索来源可信度评分
- [ ] 多语言支持

---

## License

MIT

---

🤖 由 AI 辅助开发 · [Issues](https://github.com/Gunaie/ReportAgent/issues) · [PRs](https://github.com/Gunaie/ReportAgent/pulls)
