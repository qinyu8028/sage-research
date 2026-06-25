<div align="center">

[中文](README.zh-CN.md)

</div>

<div align="center">

# SAGE Research

**S**earch · **A**nalyze · **G**enerate · **E**valuate

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An autonomous multi-agent research system that turns a question into a cited, structured report — with iterative quality review, parallel web/academic search, and a local knowledge base.

</div>



## Features

- **Multi-Agent Pipeline** — Clarifier → Supervisor → Researcher ×N → Writer, orchestrated as a LangGraph state graph. The Supervisor decomposes research questions into parallel sub-tasks and reviews results against 5 evidence-based criteria with a strict decision tree — sub-par research is automatically retried or replanned, up to 3 rounds.
- **Fault Tolerance** — Multi-layer error recovery across the pipeline: search engines fall back between providers (Brave → Tavily); tool calls that fail are retried with backoff; weak-model tool_call parsing falls back to JSON extraction from text; MCP transport errors (e.g. RefCell contention) are caught and retried transparently. Failures surface as degraded results, not crashed runs.
- **Context Engineering** — Token counting, history compaction, and context budgeting keep each agent within its context window across multi-turn ReAct loops. Per-agent temperature tuning separates structured reasoning (0) from creative generation (0.3–0.6).
- **Cost-Aware Tool Selection** — Researchers classify tools by cost tier (search snippets vs. full-page fetch vs. paper reading) and only escalate when snippets lack the specific data needed, reducing unnecessary API calls.
- **RAG Knowledge Base** — Upload PDFs, Markdown files, or arXiv papers to build a local document library. Documents are chunked, embedded, and indexed into a hybrid retrieval pipeline (BM25 + dense vector + Cross-Encoder reranking). Generated reports are automatically saved back to the library, so follow-up research can build on prior results.
- **MCP Tool Integration** — Search engines, academic APIs, and file converters are loaded dynamically via Model Context Protocol, with per-agent tool whitelists defined in config rather than code.
- **Streaming Web Interface** — Real-time research progress timeline via SSE, interactive report with citation navigation and PDF export.

## Quick Start

### 1. Clone and configure

```bash
git clone git@github.com:qinyu8028/sage-research.git
cd sage-research
cp .env.example .env
```

### 2. Get API keys (all free tier)

| Service | Sign up | Variable in `.env` |
|---------|---------|-------------------|
| **DeepSeek** (LLM) | [platform.deepseek.com](https://platform.deepseek.com) | `DEEPSEEK_API_KEY` |
| **Brave Search** | [brave.com/search/api](https://brave.com/search/api/) | `BRAVE_API_KEY` |
| **Tavily** | [tavily.com](https://tavily.com) | `TAVILY_API_KEY` |

Edit `.env` and fill in these three keys. That's the minimum to run.

> **Switching LLM providers:** set `LLM_MODEL_ID` to your model name. The system auto-detects the provider by prefix — `deepseek-*`, `glm-*`, `gemini-*`, `gpt-*`, `qwen-*` route to the corresponding API credentials. Claude models are supported via a built-in Anthropic SDK adapter. Only the active provider's key is needed.

### 3. Run

```bash
./setup.sh
```

The script creates a conda environment, installs Python/Node dependencies, and starts both backend (:8000) and frontend (:3000). Open http://localhost:3000.

### Manual startup

```bash
conda activate deep-research
python server.py &        # Backend — FastAPI on :8000
cd web && npm run dev      # Frontend — Next.js on :3000
```

### CLI mode

```bash
conda activate deep-research
python main.py "your research question"
python main.py --model deepseek-v4-flash --max-rounds 2
```

## Architecture

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

## Project Structure

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

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/clarify` | Analyze query clarity, suggest directions if ambiguous |
| POST | `/api/clarify/refine` | Refine query with user feedback into research brief |
| POST | `/api/research` | Run full pipeline, stream progress via SSE |
| GET | `/api/library` | List indexed documents |
| POST | `/api/library/upload` | Upload file (PDF/Markdown) to knowledge base |
| POST | `/api/library/save-report` | Save generated report to knowledge base |
| POST | `/api/library/ingest` | Ingest document by arXiv ID or file path |
| DELETE | `/api/library/{title}` | Remove document from knowledge base |

## Environment Variables

The system auto-detects your LLM provider from the model name prefix. Only configure the provider you use.

**LLM (choose one provider):**

| Provider | `LLM_MODEL_ID` | Required env vars |
|----------|----------------|-------------------|
| DeepSeek | `deepseek-v4-flash` | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` |
| Zhipu GLM | `glm-4-flash` | `GLM_API_KEY`, `GLM_BASE_URL` |
| Google Gemini | `gemini-2.5-flash` | `GOOGLE_API_KEY`, `GOOGLE_BASE_URL` |
| OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| Alibaba Qwen | `qwen-plus` | `QWEN_API_KEY`, `QWEN_BASE_URL` |

**Embedding:**

| Variable | Description |
|----------|-------------|
| `EMBEDDING_MODEL_ID` | Embedding model, default `embedding-3` (Zhipu embedding model)|
| `EMBEDDING_BASE_URL` | Embedding API endpoint |

**Search (at least one required, strongly recommend both):**

| Variable | Description |
|----------|-------------|
| `BRAVE_API_KEY` | Brave Search — [free tier](https://brave.com/search/api/) |
| `TAVILY_API_KEY` | Tavily Search — [free tier](https://tavily.com) |

**Optional:**

| Variable | Description |
|----------|-------------|
| `REVIEW_MODEL_ID` | Use a different model for quality review (e.g. `qwen3.7-plus`). Enables cross-model review to reduce self-consistency bias |
| `GITHUB_TOKEN` | GitHub API — enables code/repo search |
| `HF_TOKEN` | HuggingFace — enables faster Cross-Encoder reranker download |
| `http_proxy` / `https_proxy` | Network proxy |

## Tool Inventory

Researchers select from these tools at each ReAct step, classified by cost tier:

| Tool | Source | Cost Tier | Description |
|------|--------|-----------|-------------|
| `search` | Built-in | Low | Web search via Brave (primary) with Tavily fallback. Returns ranked snippets |
| `mcp__fetch__fetch` | MCP | High | Fetch full page content from a URL. Results pass through LLM denoising |
| `mcp__paper-search__search_arxiv` | MCP | Low | Search arXiv papers by keyword. Returns titles, abstracts, and IDs |
| `mcp__paper-search__search_google_scholar` | MCP | Low | Search Google Scholar. Returns titles, snippets, and links |
| `read_arxiv_paper` | Built-in | High | Download and read an arXiv paper by ID via pdfmux conversion |
| `mcp__github__search_repositories` | MCP | Low | Search GitHub repositories by keyword |
| `mcp__github__search_code` | MCP | Low | Search code across GitHub repositories |
| `rag_search` | Built-in | Free | Query the local RAG knowledge base (BM25 + vector + reranker) |

Tool whitelists are configured per agent in `configs/agents.json`. MCP servers are defined in `configs/mcp_servers.json`.

## Tech Stack

**Backend:** Python 3.14, LangGraph, FastAPI, OpenAI SDK, MCP

**Frontend:** Next.js 16, React 19, Tailwind CSS 4

**Retrieval:** Sentence-Transformers, BM25 + vector hybrid search, Cross-Encoder reranking

**Data Sources:** Brave Search, Tavily, arXiv, Google Scholar, GitHub API

## Frontend Preview

![Frontend Preview](assets/screenshot.png)
