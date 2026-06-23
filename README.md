<div align="center">

# SAGE Research

**S**earch · **A**nalyze · **G**enerate · **E**valuate

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An autonomous multi-agent research system. Ask a question, get a cited research report with inline references, rendered math, and PDF export.

</div>

## Features

- **Multi-Agent Pipeline** — Clarifier (scope refinement) → Supervisor (plan + review) → Researcher ×N (parallel search) → Writer (report synthesis). Up to 3 rounds of iterative refinement via LangGraph.
- **Web Interface** — Next.js chat UI with streaming typewriter animations, research progress timeline, interactive report view with citation navigation, and PDF export.
- **Hybrid Search** — Brave Search + Tavily (fallback), arXiv + Google Scholar (academic), GitHub code search.
- **Local Knowledge Base** — RAG pipeline (chunking → embedding → hybrid retrieval → Cross-Encoder reranking). Upload PDFs, markdown, or arXiv papers; generated reports auto-index.
- **Quality Review** — 5-criteria evidence scoring (relevance, depth, citations, sources, completeness) with three-verdict routing (approved/retry/revise).
- **Mock Mode** — Frontend runs independently without backend for UI development and demos.
- **Math Rendering** — LaTeX formula support ($...$ and $$...$$) via KaTeX.

## Quick Start

```bash
git clone git@github.com:qinyu8028/sage-research.git
cd sage-research
./setup.sh
```

The script handles everything: conda environment, Python/Node dependencies, `.env` bootstrap, and starts both services. Open http://localhost:3000 in your browser.

## Development

### Backend Only

```bash
conda activate deep-research
python server.py          # FastAPI on :8000
```

### Frontend Only (real backend)

```bash
cd web
npm install
npm run dev               # Next.js on :3000, assumes backend on :8000
```

### Frontend Only (mock mode, no backend)

```bash
cd web
npm install
npm run dev:mock          # Simulated SSE research pipeline
```

### CLI Mode

```bash
conda activate deep-research
python -m sage_research.main
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
tests/          — Unit + integration tests
data/           — Runtime data (RAG index, downloads, library)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/clarify` | Analyze query clarity, return directions if ambiguous |
| POST | `/api/clarify/refine` | Refine query with user feedback into research brief |
| POST | `/api/research` | Run full research pipeline (SSE stream) |
| GET | `/api/library` | List indexed documents |
| POST | `/api/library/upload` | Upload file (PDF/MD/TXT) to knowledge base |
| POST | `/api/library/save-report` | Save generated report to knowledge base |
| POST | `/api/library/ingest` | Ingest document by arXiv ID or file path |
| DELETE | `/api/library/{title}` | Remove document from knowledge base |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GLM_API_KEY` | Yes | Zhipu GLM API key |
| `LLM_MODEL_ID` | Yes | Model: `deepseek-v4-flash` or `glm-4.7` |
| `GLM_BASE_URL` | Yes | GLM API endpoint |
| `DEEPSEEK_API_KEY` | No | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | No | DeepSeek API endpoint |
| `EMBEDDING_MODEL_ID` | Yes | Embedding model name |
| `EMBEDDING_BASE_URL` | Yes | Embedding API endpoint |
| `BRAVE_API_KEY` | No | Brave Search API key |
| `TAVILY_API_KEY` | No | Tavily Search API key |
| `HF_TOKEN` | No | HuggingFace token for reranker |
| `GITHUB_TOKEN` | No | GitHub API token for code search |
| `ARXIV_DOWNLOAD_DIR` | No | arXiv PDF download directory |
| `RAG_DATA_DIR` | No | RAG data directory |
| `http_proxy` / `https_proxy` | No | HTTP/S proxy for API calls |

## Tech Stack

**Backend:** Python 3.14, LangGraph, FastAPI, Uvicorn, Pydantic, OpenAI SDK, MCP

**Frontend:** Next.js 16, React 19, Tailwind CSS 4, KaTeX, ReactMarkdown, rehype-raw

**Search:** Brave Search, Tavily, arXiv API, Google Scholar, GitHub API

**RAG:** Sentence-Transformers, Jieba, BM25, PyTorch, Cross-Encoder
