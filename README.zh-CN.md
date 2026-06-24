<div align="right">

[English](README.md)

</div>

<div align="center">

# SAGE Research

**S**earch · **A**nalyze · **G**enerate · **E**valuate

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

一个自主多 Agent 研究系统。提出问题，获得带有行内引用、数学公式渲染和 PDF 导出的结构化研究报告。

</div>

## 功能特性

- **多 Agent 管线** — Clarifier（范围澄清）→ Supervisor（规划 + 审查）→ Researcher ×N（并行搜索）→ Writer（报告合成）。通过 LangGraph 实现最多 3 轮迭代优化。
- **Web 界面** — Next.js 聊天界面，支持流式打字机动画、研究进度时间线、带引用跳转的交互式报告视图和 PDF 导出。
- **混合搜索** — Brave Search + Tavily（自动回退）、arXiv + Google Scholar（学术搜索）、GitHub 代码搜索。
- **本地知识库** — RAG 管线（分块 → 向量化 → 混合检索 → Cross-Encoder 重排序）。支持上传 PDF、Markdown 和 arXiv 论文；生成的报告自动入库。
- **质量审查** — 5 维度证据评分（相关性、深度、引用、来源、完整性），三种判定路由（通过/重试/修订）。
- **Mock 模式** — 前端无需后端即可独立运行，用于 UI 开发和演示。
- **数学公式渲染** — 支持 LaTeX 公式（$...$ 和 $$...$$），基于 KaTeX。

## 快速开始

```bash
git clone git@github.com:qinyu8028/sage-research.git
cd sage-research
./setup.sh
```

脚本会自动处理一切：conda 环境、Python/Node 依赖、`.env` 引导配置，并启动前后端服务。在浏览器中打开 http://localhost:3000。

## 开发指南

### 仅启动后端

```bash
conda activate deep-research
python server.py          # FastAPI 运行在 :8000
```

### 仅启动前端（连接真实后端）

```bash
cd web
npm install
npm run dev               # Next.js 运行在 :3000，默认连接后端 :8000
```

### 仅启动前端（Mock 模式，无需后端）

```bash
cd web
npm install
npm run dev:mock          # 模拟完整 SSE 研究管线
```

### CLI 模式

```bash
conda activate deep-research
python -m sage_research.main
```

## 架构

```
        User Query
            │
            ▼
            ┌───────────┐   unclear    ┌─────────────────┐
            │ Clarifier │────────────▶│  User Feedback  │
            └─────┬─────┘              └────────┬────────┘
                  │ clear                       │
                  ▼                             ▼
            research_brief ◀───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      LangGraph Pipeline                     │
│                                                             │
│               ┌────────────────────┐                        │
│               │  Supervisor.plan() │                        │
│               └─────────┬──────────┘                        │
│                         │                                   │
│                 ┌───────┼──────┐                            │
│                 ▼       ▼      ▼                            │
│               ┌────┐ ┌────┐ ┌────┐                          │
│               │ R1 │ │ R2 │ │ R3 │  (parallel Researchers)  │
│               └──┬─┘ └──┬─┘ └──┬─┘                          │
│                  └──────┼──────┘                            │
│                         ▼                                   │
│                ┌─────────────────────┐                      │
│                │ Supervisor.review() │                      │
│                └─────────┬───────────┘                      │
│                          │                                  │
│                   ┌──────┴──────┐                           │
│                   ▼             ▼                           │
│               approved     retry/revise                     │
│                   │             └──▶ back to plan (max 3)  │
│                   ▼                                         │
│               ┌────────┐                                    │
│               │ Writer │                                    │
│               └────┬───┘                                    │
│                    │                                        │
│                    ▼                                        │
│            Research Report ──▶ auto-index to RAG           │
└─────────────────────────────────────────────────────────────┘
```

## 项目结构

```
sage_research/
├── base/       — LLMClient, AgentBase, Message, Config, Logger
├── agents/     — Clarifier, Supervisor, Researcher, Writer
├── tools/      — BaseTool, ToolRegistry, RAGTool, PaperReaderTool
├── search/     — SearchTool (Brave+Tavily 回退), Adapters
├── mcp/        — MCPClient, MCPTool, register_mcp_tools
├── context/    — TokenCounter, Truncator, HistoryCompactor, ContextBuilder
├── rag/        — Chunker, Embedding, VectorStore, Reranker, MQE, Pipeline
├── graph/      — LangGraph 状态图（State + nodes + routing）
├── library/    — 文档转换器, LibraryManager（ingest/list/delete）
├── api/        — FastAPI 应用, Pydantic schemas, SSE 事件格式化
└── orchestrator.py — 基础设施搭建, 研究执行器, 资源管理

web/            — Next.js 前端
├── app/        — 页面布局, 全局样式
├── components/ — ClarifyPanel, ResearchProgress, ReportView,
│                 LibraryDrawer, StreamingText, QueryInput
└── lib/        — API 客户端, mock SSE 模拟

configs/        — MCP 服务器配置, Agent 工具白名单
tests/          — 单元测试 + 集成测试
data/           — 运行时数据（RAG 索引, 下载, 文献库）
```

## API 端点

| Method | Path | 描述 |
|--------|------|------|
| POST | `/api/clarify` | 分析查询明确度，不明确时返回研究方向建议 |
| POST | `/api/clarify/refine` | 将用户反馈整合为研究简述 |
| POST | `/api/research` | 运行完整研究管线（SSE 流） |
| GET | `/api/library` | 列出已索引的文献 |
| POST | `/api/library/upload` | 上传文件（PDF/MD/TXT）到知识库 |
| POST | `/api/library/save-report` | 将生成的报告保存到知识库 |
| POST | `/api/library/ingest` | 通过 arXiv ID 或文件路径导入文献 |
| DELETE | `/api/library/{title}` | 从知识库中删除文献 |

## 环境变量

| 变量 | 必填 | 描述 |
|----------|----------|-------------|
| `GLM_API_KEY` | 是 | 智谱 GLM API 密钥 |
| `LLM_MODEL_ID` | 是 | 模型选择：`deepseek-v4-flash` 或 `glm-4.7` |
| `GLM_BASE_URL` | 是 | GLM API 端点 |
| `DEEPSEEK_API_KEY` | 否 | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | 否 | DeepSeek API 端点 |
| `EMBEDDING_MODEL_ID` | 是 | 嵌入模型名称 |
| `EMBEDDING_BASE_URL` | 是 | 嵌入 API 端点 |
| `BRAVE_API_KEY` | 否 | Brave Search API 密钥 |
| `TAVILY_API_KEY` | 否 | Tavily Search API 密钥 |
| `HF_TOKEN` | 否 | HuggingFace token（用于 reranker） |
| `GITHUB_TOKEN` | 否 | GitHub API token（用于代码搜索） |
| `ARXIV_DOWNLOAD_DIR` | 否 | arXiv PDF 下载目录 |
| `RAG_DATA_DIR` | 否 | RAG 数据目录 |
| `http_proxy` / `https_proxy` | 否 | HTTP/S 代理 |

## 技术栈

**后端：** Python 3.14, LangGraph, FastAPI, Uvicorn, Pydantic, OpenAI SDK, MCP

**前端：** Next.js 16, React 19, Tailwind CSS 4, KaTeX, ReactMarkdown, rehype-raw

**搜索：** Brave Search, Tavily, arXiv API, Google Scholar, GitHub API

**RAG：** Sentence-Transformers, Jieba, BM25, PyTorch, Cross-Encoder
