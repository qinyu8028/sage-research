<div align="right">

[English](README.md)

</div>

<div align="center">

# SAGE Research

**S**earch · **A**nalyze · **G**enerate · **E**valuate

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

一个自主多 Agent 研究系统，将一个问题转化为带引用的结构化研究报告 -- 支持迭代质量审查、并行网络/学术搜索和本地知识库。

</div>



## 功能特性

- **多 Agent 管线** -- Clarifier -> Supervisor -> Researcher xN -> Writer，以 LangGraph 状态图编排。Supervisor 将研究问题分解为并行子任务，并按 5 项基于证据的标准和严格决策树审查结果 -- 不达标的研究自动重试或重新规划，最多 3 轮。
- **容错机制** -- 管线全链路多层错误恢复：搜索引擎在提供商之间回退（Brave -> Tavily）；失败的工具调用带退避重试；弱模型 tool_call 解析回退到从文本提取 JSON；MCP 传输错误（如 RefCell 竞争）被透明捕获和重试。故障表现为降级结果，而非崩溃。
- **上下文工程** -- Token 计数、历史压缩和上下文预算管理使每个 Agent 在多轮 ReAct 循环中保持在上下文窗口内。按 Agent 调节温度，将结构化推理（0）与创意生成（0.3-0.6）分离。
- **成本感知工具选择** -- Researcher 按成本分级分类工具（搜索摘要 vs. 全页抓取 vs. 论文阅读），仅在摘要缺少所需的具体数据时才升级调用，减少不必要的 API 开销。
- **RAG 知识库** -- 上传 PDF、Markdown 文件或 arXiv 论文构建本地文献库。文档经分块、向量化后进入混合检索管线（BM25 + 稠密向量 + Cross-Encoder 重排序）。生成的报告自动回存至知识库，后续研究可在先前结果上递进。
- **MCP 工具集成** -- 搜索引擎、学术 API 和文件转换器通过 Model Context Protocol 动态加载，每个 Agent 的工具白名单在配置中定义而非硬编码。
- **流式 Web 界面** -- 通过 SSE 实时展示研究进度时间线，交互式报告支持引用导航和 PDF 导出。

## 快速开始

### 1. 克隆并配置

```bash
git clone git@github.com:qinyu8028/sage-research.git
cd sage-research
cp .env.example .env
```

### 2. 获取 API 密钥（均有免费额度）

| 服务 | 注册地址 | `.env` 中的变量 |
|------|---------|----------------|
| **DeepSeek**（LLM） | [platform.deepseek.com](https://platform.deepseek.com) | `DEEPSEEK_API_KEY` |
| **Brave Search** | [brave.com/search/api](https://brave.com/search/api/) | `BRAVE_API_KEY` |
| **Tavily** | [tavily.com](https://tavily.com) | `TAVILY_API_KEY` |

编辑 `.env` 填入上述三个密钥，即可运行。

> **切换 LLM 提供商：** 将 `LLM_MODEL_ID` 设为你的模型名称。系统通过前缀自动识别提供商 -- `deepseek-*`、`glm-*`、`gemini-*`、`gpt-*`、`qwen-*` 分别路由到对应的 API 凭证。Claude 模型通过内置 Anthropic SDK 适配器支持。只需配置当前使用的提供商的密钥。

### 3. 运行

```bash
./setup.sh
```

脚本会创建 conda 环境、安装 Python/Node 依赖，并启动后端（:8000）和前端（:3000）。打开 http://localhost:3000。

### 手动启动

```bash
conda activate deep-research
python server.py &        # 后端 -- FastAPI 运行在 :8000
cd web && npm run dev      # 前端 -- Next.js 运行在 :3000
```

### CLI 模式

```bash
conda activate deep-research
python main.py "你的研究问题"
python main.py --model deepseek-v4-flash --max-rounds 2
```

## 架构

```
            User Query
                  |
                  v
            +───────────+   unclear    +─────────────────+
            | Clarifier |────────────>|  User Feedback  |
            +─────┬─────+              +────────┬────────+
                  | clear                       |
                  v                             v
            research_brief <───────────────────+
                  |
                  v
+─────────────────────────────────────────────────────────────+
|                      LangGraph Pipeline                     |
|                                                             |
|               +────────────────────+                        |
|               |  Supervisor.plan() |                        |
|               +─────────┬──────────+                        |
|                         |                                   |
|                 +───────┼──────+                            |
|                 v       v      v                            |
|               +────+ +────+ +────+                          |
|               | R1 | | R2 | | R3 |  (parallel Researchers)  |
|               +──┬─+ +──┬─+ +──┬─+                          |
|                  +──────┼──────+                            |
|                         v                                   |
|                +─────────────────────+                      |
|                | Supervisor.review() |                      |
|                +─────────┬───────────+                      |
|                          |                                  |
|                   +──────┴──────+                           |
|                   v             v                           |
|               approved     retry/revise                     |
|                   |             +──> back to plan (max 3)  |
|                   v                                         |
|               +────────+                                    |
|               | Writer |                                    |
|               +────┬───+                                    |
|                    |                                        |
|                    v                                        |
|            Research Report ──> auto-index to RAG           |
+─────────────────────────────────────────────────────────────+
```

## 项目结构

```
sage_research/
├── base/       — LLMClient, AgentBase, Message, Config, Logger
├── agents/     — Clarifier, Supervisor, Researcher, Writer
├── tools/      — BaseTool, ToolRegistry, RAGTool, PaperReaderTool
├── search/     — SearchTool (Brave+Tavily fallback), Adapters
├── mcp/        — MCPClient, MCPTool, register_mcp_tools
├── context/    — TokenCounter, Truncator, HistoryCompactor, ContextBuilder
├── rag/        — Chunker, Embedding, VectorStore, Reranker, MQE, Pipeline
├── graph/      — LangGraph state graph (State + nodes + routing)
├── library/    — Document converter, LibraryManager (ingest/list/delete)
├── api/        — FastAPI app, Pydantic schemas, SSE event formatting
└── orchestrator.py — Infrastructure setup, research runner, resource management

web/            — Next.js frontend
├── app/        — Page layout, global styles
├── components/ — ClarifyPanel, ResearchProgress, ReportView,
│                 LibraryDrawer, StreamingText, QueryInput
└── lib/        — API client, mock SSE simulation

configs/        — MCP server config, agent tool whitelists
data/           — Runtime data (RAG index, downloads, library)
```

## API 端点

| Method | Path | 描述 |
|--------|------|------|
| POST | `/api/clarify` | 分析查询明确度，模糊时返回研究方向建议 |
| POST | `/api/clarify/refine` | 将用户反馈整合为研究简述 |
| POST | `/api/research` | 运行完整管线，通过 SSE 流式输出进度 |
| GET | `/api/library` | 列出已索引的文献 |
| POST | `/api/library/upload` | 上传文件（PDF/Markdown）到知识库 |
| POST | `/api/library/save-report` | 将生成的报告保存到知识库 |
| POST | `/api/library/ingest` | 通过 arXiv ID 或文件路径导入文献 |
| DELETE | `/api/library/{title}` | 从知识库中删除文献 |

## 环境变量

系统通过模型名称前缀自动识别 LLM 提供商。只需配置当前使用的提供商。

**LLM（选择一个提供商）：**

| 提供商 | `LLM_MODEL_ID` | 所需环境变量 |
|--------|----------------|-------------|
| DeepSeek | `deepseek-v4-flash` | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` |
| Zhipu GLM | `glm-4-flash` | `GLM_API_KEY`, `GLM_BASE_URL` |
| Google Gemini | `gemini-2.5-flash` | `GOOGLE_API_KEY`, `GOOGLE_BASE_URL` |
| OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| Alibaba Qwen | `qwen-plus` | `QWEN_API_KEY`, `QWEN_BASE_URL` |

**Embedding：**

| 变量 | 描述 |
|------|------|
| `EMBEDDING_MODEL_ID` | Embedding 模型，默认 `embedding-3`（智谱 embedding 模型） |
| `EMBEDDING_BASE_URL` | Embedding API 端点 |

**搜索（至少需要一个，强烈建议两个都配置）：**

| 变量 | 描述 |
|------|------|
| `BRAVE_API_KEY` | Brave Search -- [免费额度](https://brave.com/search/api/) |
| `TAVILY_API_KEY` | Tavily Search -- [免费额度](https://tavily.com) |

**可选：**

| 变量 | 描述 |
|------|------|
| `REVIEW_MODEL_ID` | 使用不同模型进行质量审查（如 `qwen3.7-plus`），启用跨模型审查以减少自一致性偏差 |
| `GITHUB_TOKEN` | GitHub API -- 启用代码/仓库搜索 |
| `HF_TOKEN` | HuggingFace -- 加速 Cross-Encoder reranker 下载 |
| `http_proxy` / `https_proxy` | 网络代理 |

## 工具清单

Researcher 在每个 ReAct 步中从以下工具中选择，按成本分级：

| 工具 | 来源 | 成本 | 描述 |
|------|------|------|------|
| `search` | 内置 | 低 | 网页搜索，Brave 优先 + Tavily 回退。返回排序摘要 |
| `mcp__fetch__fetch` | MCP | 高 | 抓取完整网页内容。结果经 LLM 去噪 |
| `mcp__paper-search__search_arxiv` | MCP | 低 | 按关键词搜索 arXiv 论文，返回标题、摘要和 ID |
| `mcp__paper-search__search_google_scholar` | MCP | 低 | 搜索 Google Scholar，返回标题、摘要和链接 |
| `read_arxiv_paper` | 内置 | 高 | 通过 pdfmux 下载并阅读 arXiv 论文 |
| `mcp__github__search_repositories` | MCP | 低 | 按关键词搜索 GitHub 仓库 |
| `mcp__github__search_code` | MCP | 低 | 跨仓库搜索 GitHub 代码 |
| `rag_search` | 内置 | 免费 | 查询本地 RAG 知识库（BM25 + 向量 + 重排序） |

工具白名单按 Agent 配置在 `configs/agents.json`，MCP 服务器定义在 `configs/mcp_servers.json`。

## 技术栈

**后端：** Python 3.14, LangGraph, FastAPI, OpenAI SDK, MCP

**前端：** Next.js 16, React 19, Tailwind CSS 4

**检索：** Sentence-Transformers, BM25 + 向量混合检索, Cross-Encoder 重排序

**数据源：** Brave Search, Tavily, arXiv, Google Scholar, GitHub API

## 前端预览

![前端预览](assets/screenshot.png)
