<div align="center">

# SAGE Research

**S**earch · **A**nalyze · **G**enerate · **E**valuate

An autonomous multi-agent research system that breaks down complex questions,
searches across web and academic sources in parallel, and synthesizes structured research reports.

</div>

## Features

- **Multi-Agent Pipeline** — Clarifier → Supervisor → Researcher ×N → Reviewer → Writer, orchestrated by LangGraph with iterative refinement (up to 3 rounds)
- **Hybrid RAG** — Vector search + BM25 + RRF fusion + Cross-Encoder reranking; research reports auto-indexed for future retrieval
- **MCP Tool Ecosystem** — Brave Search, Tavily, arXiv, Google Scholar, GitHub, PDF reader via Model Context Protocol
- **Quality Gates** — Supervisor review with 4-criteria evidence scoring (relevance, depth, citations, sources), three-verdict routing (approved/retry/revise)
- **Robustness** — Search fallback (Brave → Tavily), ReAct self-correction, tool result denoising, weak-model fallback parsing
- **FastAPI Server** — REST + SSE streaming endpoints for web frontend integration
- **Document Library** — Ingest arXiv papers, PDFs, and markdown into the shared RAG knowledge base

## Architecture

```
User Query
    │
    ▼
┌───────────┐   unclear    ┌─────────────────┐
│ Clarifier │─────────────▶│  User Feedback  │
└─────┬─────┘              └────────┬────────┘
      │ clear                       │
      ▼                             ▼
research_brief ◀────────────────────┘
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

## Tech Stack

- **LLM**: Multi-model support (GLM-4-Flash, DeepSeek, Qwen) via prefix routing
- **Orchestration**: LangGraph (state graph with conditional routing and parallel fan-out)
- **Search**: Brave Search + Tavily (fallback)
- **Academic**: paper-search-mcp (arXiv + Google Scholar)
- **RAG**: Custom pipeline (chunking → embedding → hybrid retrieval → reranking)
- **Backend**: FastAPI + SSE streaming
- **Tools**: MCP protocol + custom tool registry with per-agent whitelists

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
```

## Quick Start

```bash
git clone git@github.com:qinyu8028/sage-research.git
cd sage-research

conda create -n deep-research python=3.14
conda activate deep-research
pip install -r requirements.txt

# Configure API keys in .env
cp .env.example .env

# CLI mode
python -m sage_research.main

# Server mode (FastAPI)
python server.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/clarify` | Analyze query clarity, return directions if ambiguous |
| POST | `/api/clarify/refine` | Refine query with user feedback into research brief |
| POST | `/api/research` | Run full research pipeline (SSE stream) |
| GET | `/api/library` | List indexed documents |
| POST | `/api/library/ingest` | Add document to knowledge base |
| DELETE | `/api/library/{title}` | Remove document from knowledge base |
