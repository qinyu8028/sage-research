# 🔍 Sage Research

**SAGE** — Search, Analyze, Generate, Evaluate

An autonomous multi-agent research system that breaks down complex questions, searches across web and academic sources in parallel, and synthesizes structured research reports.

## ✨ Features

- **Multi-Agent Architecture** — Router → Supervisor → Researcher ×N → Reviewer → Writer
- **Hybrid Retrieval** — Vector search + BM25 + RRF fusion + Cross-Encoder reranking
- **MCP Integration** — Extensible tool system via Model Context Protocol
- **Quality Gates** — Retrieval relevance scoring, query rewriting, coverage assessment
- **Robustness** — Tool fallback, error recovery, graceful degradation
- **Memory System** — Cross-session knowledge accumulation (working + semantic memory)

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────┐     ┌──────────────┐
│  Router  │────▶│ Scope Clarify │
└─────────┘     └──────┬───────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Supervisor    │◀──── coverage check
              └────────┬────────┘
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
      ┌──────────┐┌──────────┐┌──────────┐
      │Researcher││Researcher││Researcher│
      └────┬─────┘└────┬─────┘└────┬─────┘
           │           │           │
           └───────────┼───────────┘
                       ▼
              ┌─────────────────┐
              │    Reviewer     │──── not enough? → back to Supervisor
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     Writer      │
              └────────┬────────┘
                       │
                       ▼
                 Research Report
```

## 🛠️ Tech Stack

- **LLM**: GLM-4-Flash (128K context)
- **Orchestration**: LangGraph
- **Search**: Brave Search + Tavily (fallback)
- **Academic**: paper-search-mcp (25+ sources)
- **RAG**: Custom pipeline (chunking → embedding → hybrid retrieval → reranking)
- **Memory**: Working memory (TTL) + Semantic memory (persistent)

## 📦 Project Structure

```
sage_research/
├── base/       — Message, LLMClient, AgentBase, Config
├── agents/     — Router, Supervisor, Researcher, Reviewer, Writer
├── tools/      — Tool base class, Registry
├── mcp/        — MCP Client, Tool Adapter
├── context/    — Token counting, truncation, history compression
├── memory/     — Working + Semantic memory, Manager
├── rag/        — Chunker, Embedding, VectorStore, Reranker, Pipeline
└── graph/      — LangGraph state graph definitions
```

## 🚀 Quick Start

```bash
# Clone
git clone git@github.com:qinyu8028/sage-research.git
cd sage-research

# Environment
conda create -n deep-research python=3.14
conda activate deep-research
pip install -r requirements.txt

# Configure
# Add API keys to .env (GLM_API_KEY, BRAVE_API_KEY, etc.)

# Run
python -m sage_research.main
```
