# Deep Walkthrough
![Banner](/assets/banner.png)

<div align="center">

### Research Intelligence System

**A production-grade, fully observable multi-agent reference implementation.**  
Built to teach AI agent patterns correctly — by building one that actually works.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-stateful_graph-1C3C3C?style=flat-square)](https://langchain-ai.github.io/langgraph)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=flat-square&logo=openai&logoColor=white)](https://openai.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](./LICENSE)

 [Architecture](#architecture) · [Quick Start](#quick-start) · [API Reference](#api-reference) · [Contributing](#contributing)

</div>

## Architecture

### Agent Pipeline

```
┌───────────┐  Gate 1   ┌───────────┐  Gate 2   ┌──────────────┐
│ Supervisor│──────────▶│ Retrieval │──────────▶│  Supervisor  │
│  (plan)   │ Plan rev. │  (ReAct)  │ Src. rev. │ (post_sources)│
└───────────┘           └─────▲─────┘           └──────┬───────┘
                              │                        │
                  loop back ──┘            ┌───────────▼───────────┐
                  (more sources needed)    │       Analysis        │
                                           └───────────┬───────────┘
                                                       │
                                           ┌───────────▼───────────┐
                                           │      Supervisor       │
                                           │    (post_analysis)    │
                                           └───────────┬───────────┘
                                                       │
                                           ┌───────────▼───────────┐
                                ┌─────────▶│       Synthesis       │
                                │          └───────────┬───────────┘
                                │                      │
                                │          ┌───────────▼───────────┐
                                │          │        Critic         │
                                │          └───────────┬───────────┘
                                │                      │
                                │          ┌───────────▼───────────┐
                                └──────────│      Supervisor       │──▶ Final Report
                                  revise   │    (post_critic)      │   (end)
                                           └───────────────────────┘
```

**Gate 1 — Plan Approval:** The Supervisor decomposes the query into sub-questions and presents the plan. You approve, edit, or reject before any retrieval begins.

**Gate 2 — Source Approval:** The Retrieval Agent surfaces its candidates with credibility scores. You deselect untrusted sources. Analysis and Synthesis only ever see what you approved.

**True Supervisor pattern:** The Supervisor is a real orchestrator, not a one-shot planner. After Gate 1 it re-enters the graph at three checkpoints — `post_sources`, `post_analysis`, and `post_critic` — reads the accumulated `AgentState`, and emits a structured `SupervisorDecision` that drives the conditional edges. There are no hardcoded threshold checks in the graph; every loop-back, advance, and termination is a reasoned LLM decision.

| Checkpoint | Reads | Routes to |
|---|---|---|
| `post_sources` | `approved_sources`, credibility, sub-question coverage | `analysis` or `retrieval` (loop back with a directive) |
| `post_analysis` | `claims`, `analysis_gaps`, `revision_count` | `synthesis` or `retrieval` (only when gaps are critical) |
| `post_critic` | `critic_score`, `critic_feedback`, `revision_count` | `synthesis` (revise) or `end` |

Each decision carries an `instruction` field — a directive the next worker agent reads from `current_supervisor_instruction` and injects into its prompt. Every decision is appended to `supervisor_decisions` and surfaced as a `supervisor_decision` SSE event, rendered as a stage-divider card in the agent timeline.

---

### Backend

```
FastAPI (async)
└── LangGraph stateful graph
    ├── Supervisor (plan)         — CoT planner, decomposes query into sub-questions
    ├── [HITL Gate 1]              — plan approval interrupt
    ├── Retrieval Agent            — ReAct loop: web search + session-scoped vector store
    ├── [HITL Gate 2]              — source approval interrupt
    ├── Supervisor (post_sources)  — routes to analysis or back to retrieval
    ├── Analysis Agent             — claim extraction + gap identification
    ├── Supervisor (post_analysis) — routes to synthesis or back to retrieval
    ├── Synthesis Agent            — markdown report with chunk-level citations
    ├── Critic Agent               — scores draft + structured feedback
    └── Supervisor (post_critic)   — routes to synthesis (revise) or end
```

The three `Supervisor (post_*)` rows are all the same `supervisor_route_node` — one LangGraph node re-entered at three pipeline stages. It detects its own context by inspecting the state (presence of `claims`, `critic_score`, etc.) and selects the appropriate routing prompt.

**Memory layers:**

- **Short-term** — `AgentState` TypedDict, shared across all nodes in a run.
- **Long-term** — ChromaDB vector store, session-scoped (each session's documents are isolated by `session_id` metadata filter — no cross-session leakage).
- **Episodic** — SQLite log of sessions, HITL decisions, and per-step events. Gives the system a queryable history.

**Key design decisions:**

- Fully async — every node is `async def`, every I/O client is async. No sync blocking in the event loop.
- Single LLM via `get_llm(agent_id)` factory — swap models per agent in `config.py` without touching agent code.
- `ToolResult` contract — tools never raise exceptions. Errors are structured observations the agent reasons about.
- Full reasoning exposure — every agent's scratchpad is stored in `AgentState`. Nothing is discarded.
- Redis LLM cache — responses are cached by `sha256(model + prompt)`. Flush with `make flush-cache` for a fresh run.
- LangGraph SQLite checkpointer — full graph state is persisted across HTTP requests, enabling HITL across disconnected sessions.

---

### Frontend

Three-panel developer debug UI built in Next.js — designed for information density, not aesthetics.

```
┌────────────────────┬──────────────────────┬────────────────────┐
│  Agent Progress    │   Active Surface     │  State Inspector   │
│  Feed (SSE)        │                      │                    │
│                    │  • Tool outputs      │  Live AgentState   │
│  Timeline of       │  • HITL Gate 1       │  JSON tree         │
│  every graph step  │  • HITL Gate 2       │                    │
│  colour-coded      │  • Report preview    │  Diffs highlighted │
│  per agent         │                      │  after each node   │
│                    │                      │                    │
└────────────────────┴──────────────────────┴────────────────────┘
```

The SSE stream is the single source of truth for UI state — no polling, no refetching. Every graph node emits a `state_snapshot` event so the State Inspector updates in real time.

---

### Infrastructure

| Service | Image | Purpose |
|---|---|---|
| `backend` | Python 3.12-slim | FastAPI + LangGraph, hot reload |
| `frontend` | Node 20-alpine | Next.js dev server, hot reload |
| `chromadb` | `chromadb/chroma` | Vector store (HTTP mode) |
| `redis` | `redis:7-alpine` | LLM response cache |

SQLite is a file — no separate container. Mounted as a named volume on the backend.

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An OpenAI API key
- A Tavily API key ([free tier available](https://tavily.com))

### 1. Clone and configure

```bash
git clone https://github.com/your-org/research-intelligence-system.git
cd research-intelligence-system
cp .env.example .env
```

Edit `.env` and fill in your keys:

```bash
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

### 2. Start the stack

```bash
make up
```

First run pulls images and installs dependencies — takes a couple of minutes. Subsequent starts are fast.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| ChromaDB | http://localhost:8001 |
| Redis | localhost:6379 |

### 3. Ingest some documents (optional)

```bash
# From a local PDF
make ingest file=path/to/paper.pdf

# From a URL
make ingest-url url=https://example.com/article
```

Documents are session-scoped at ingest time. See [Session-scoped RAG](#session-scoped-rag) below.

### 4. Run a research session

Open http://localhost:3000, enter a research question, and watch the agent pipeline run live.

---

## Session-scoped RAG

Documents ingested for a session are only visible to that session. This is enforced at the database level via a `session_id` metadata filter on every ChromaDB query — not a soft convention.

When you ingest a document, you provide the `session_id` it belongs to. The Retrieval Agent always queries with `where: { session_id: { $eq: current_session_id } }`. It is structurally impossible for one session's retrieval to read another session's documents.

Documents are deleted from ChromaDB when the session completes.

---

## API Reference

### `POST /api/research`

Start a new research session.

```jsonc
// Request
{ "query": "What are the latest advances in mechanistic interpretability?" }

// Response
{ "session_id": "3f2a1b..." }
```

### `GET /api/session/{id}/stream`

Server-sent event stream. Connect immediately after creating a session. Events:

```typescript
type SessionEvent =
  | { type: "agent_start";         agent: string; node: string; timestamp: string }
  | { type: "agent_end";           agent: string; node: string; output: object; timestamp: string }
  | { type: "tool_call";           agent: string; tool: string; input: object; timestamp: string }
  | { type: "tool_result";         agent: string; tool: string; result: object; timestamp: string }
  | { type: "state_snapshot";      state: AgentState; timestamp: string }
  | { type: "hitl_interrupt";      gate: "plan" | "sources"; payload: object; timestamp: string }
  | { type: "supervisor_decision";
      stage: "post_sources" | "post_analysis" | "post_critic";
      next: "analysis" | "retrieval" | "synthesis" | "end";
      reasoning: string;
      instruction: string | null;
      timestamp: string }
  | { type: "session_complete";    report_id: string; timestamp: string }
  | { type: "error";               message: string; recoverable: boolean; timestamp: string }
```

`supervisor_decision` events are rendered as full-width stage-divider cards in the agent timeline (`SupervisorDecisionCard`), showing the routing arrow, the Supervisor's full reasoning, and the directive passed to the next agent.

### `POST /api/session/{id}/resume`

Resume a session paused at a HITL gate.

```jsonc
// Gate 1 — plan approval
{ "gate": "plan", "decision": { "action": "approve" } }
{ "gate": "plan", "decision": { "action": "edit", "plan": { "sub_questions": ["..."] } } }
{ "gate": "plan", "decision": { "action": "reject" } }

// Gate 2 — source approval
{ "gate": "sources", "decision": { "approved_chunk_ids": ["chunk_abc", "chunk_def"] } }
```

### `POST /api/ingest`

Ingest a document into a session's knowledge base. Multipart form.

```bash
# PDF
curl -X POST http://localhost:8000/api/ingest \
  -F "session_id=3f2a1b..." \
  -F "file=@paper.pdf"

# URL
curl -X POST http://localhost:8000/api/ingest \
  -F "session_id=3f2a1b..." \
  -F "url=https://example.com/article"
```

Response: `{ "doc_id": "...", "chunk_count": 42 }`

### `GET /api/report/{id}`

Returns the completed report with resolved citation metadata (source title, URL, page number, chunk text).

---

## Configuration

All configuration lives in `.env`. See `.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required |
| `TAVILY_API_KEY` | — | Required |
| `DEFAULT_MODEL` | `gpt-4o` | Model for all agents (override per-agent in `config.py`) |
| `LLM_CACHE_ENABLED` | `true` | Redis LLM response cache |
| `LLM_CACHE_TTL_SECONDS` | `3600` | Cache TTL |
| `MAX_RETRIEVAL_STEPS` | `8` | Max ReAct iterations in Retrieval Agent |
| `MAX_TOOL_RETRIES` | `3` | Consecutive tool failures before skipping a sub-question |
| `RETRIEVAL_TOP_K` | `10` | Chunks returned per vector store query |
| `CRITIC_PASS_THRESHOLD` | `0.75` | Score the Supervisor uses to decide whether to end or send the draft back for another revision |
| `MAX_REVISIONS` | `2` | Hard ceiling on Supervisor-initiated revision loops |
| `MIN_SOURCES_PER_SUBQUESTION` | `2.0` | Supervisor `post_sources` heuristic: loop back to retrieval if average coverage falls below this |
| `MIN_SOURCE_CREDIBILITY` | `0.6` | Supervisor `post_sources` heuristic: loop back if all approved sources score below this |
| `DEBUG_MODE` | `true` | Surface agent scratchpads in SSE events |

---

## Developer Commands

```bash
make up             # Start all services
make down           # Stop all services
make rebuild        # Rebuild images and restart
make logs           # Follow logs from all services
make flush-cache    # Clear Redis LLM cache (force fresh LLM calls)
make reset-db       # Wipe all volumes and restart fresh
make shell-backend  # Shell into the backend container
make shell-frontend # Shell into the frontend container
make ingest file=path/to/doc.pdf
make ingest-url url=https://example.com
```

---

## Project Structure

```
research-agent/
├── backend/
│   └── app/
│       ├── agents/         # supervisor, retrieval, analysis, synthesis, critic
│       ├── tools/          # search, retrieval, document, analysis + ToolResult base
│       ├── graph/          # AgentState, graph assembly, HITL interrupt nodes
│       ├── memory/         # ChromaDB (long-term) + SQLite (episodic) clients
│       ├── ingestion/      # PDF/URL → chunk → embed → ChromaDB pipeline
│       ├── cache/          # Redis-backed LLM response cache
│       ├── api/            # FastAPI routes + SSE streaming
│       └── config.py       # get_llm() factory, env vars, constants
├── frontend/
│   └── src/
│       ├── app/            # Next.js pages: /, /session/[id], /report/[id]
│       ├── components/     # upload, session panels, HITL, report viewer
│       ├── hooks/          # useSessionStream — SSE EventSource hook
│       └── types/          # SessionEvent union type, AgentState shape
├── docker-compose.yml
├── Makefile
├── .env.example
└── CLAUDE.md               # full design spec — read this first
```

---

## Contributing

Contributions are welcome. This project is explicitly designed to be extended — every agent, tool, and memory backend is a self-contained module.

### Good first issues

- **Add a new tool** — implement `app/tools/base.py`'s `ToolResult` contract and register it on an agent.
- **Improve hybrid retrieval** — the BM25 + dense fusion in `app/tools/retrieval.py` has room for a better reranker.
- **Add per-agent model routing** — `config.py` has the `AGENT_MODEL_MAP` ready; wire it to a UI control.
- **Episodic memory queries** — the SQLite schema is in place; build a `GET /api/sessions` endpoint and a session history panel in the frontend.
- **Export report as PDF** — the report viewer has a markdown download; a PDF export via `weasyprint` or similar would be a clean addition.

### Before you open a PR

1. Read `CLAUDE.md` — it documents all non-negotiable design decisions.
2. Tools must return `ToolResult` — never raise exceptions from a tool function.
3. New graph nodes must be `async def` and must emit appropriate SSE events.
4. Agent scratchpads must be stored in `AgentState` — never discarded.
5. Any new retrieval must use the `session_id` metadata filter — no global queries.

### Setup for development

```bash
git clone https://github.com/your-org/research-intelligence-system.git
cd research-intelligence-system
cp .env.example .env   # fill in your keys
make up
```

Backend has hot reload (`--reload` on uvicorn). Frontend has Next.js fast refresh. No rebuilds needed for code changes.

---

## License

MIT — see [LICENSE](./LICENSE).
