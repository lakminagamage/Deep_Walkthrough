Research Intelligence System
============================

This repository contains a production-grade reference implementation of a multi-agent research system. It accepts a research question and optional documents, orchestrates planning, retrieval, analysis, synthesis, and critique, and produces a cited report with human-in-the-loop approvals.

Architecture
------------

Backend (FastAPI + LangGraph):
- Fully async graph execution with a single LLM factory.
- Two approval gates: plan approval and source approval.
- Tool layer with structured error-as-observation handling.
- SSE event stream for live progress and state snapshots.
- Long-term memory in ChromaDB, episodic memory in SQLite, and optional Redis LLM cache.

Frontend (Next.js):
- Three-panel debug UI: event feed, active surface (HITL), and state inspector.
- Report viewer with citation resolution and downloadable markdown.

Agent pipeline
--------------

Supervisor -> Plan approval -> Retrieval -> Source approval -> Analysis -> Synthesis -> Critic
If the critic score is below the threshold and revision limit allows it, the graph loops back to Synthesis.

Data flow
---------

1. Ingest PDF or URL
	- Parse and chunk documents.
	- Embed and store in ChromaDB.
2. Retrieval
	- Query vector store first, then web search and URL fetch as needed.
	- Produce source candidates for approval.
3. Analysis
	- Extract claims and identify gaps from approved sources only.
4. Synthesis
	- Generate a markdown report with chunk-level citations.
5. Critic
	- Score and optionally request revisions.

Repository structure
--------------------

- backend/
  - app/agents: multi-agent nodes
  - app/tools: search, retrieval, document, and analysis tools
  - app/graph: state schema, HITL gates, and graph assembly
  - app/memory: ChromaDB and SQLite clients
  - app/api: FastAPI routes and SSE streaming
- frontend/
  - app/: Next.js pages
  - components/: debug UI and report viewer
  - hooks/: SSE client hook

API
---

POST /api/research
Request:
```json
{ "query": "...", "document_ids": ["..."] }
```
Response:
```json
{ "session_id": "..." }
```

GET /api/session/{id}/stream
- Server-sent events with graph progress, tool calls, and state snapshots.

POST /api/session/{id}/resume
Request:
```json
{ "gate": "plan", "decision": { "action": "approve" } }
```
or
```json
{ "gate": "sources", "decision": { "approved_chunk_ids": ["..."] } }
```

POST /api/ingest
- Multipart upload with PDF file or a URL form field.

GET /api/documents
- Returns ingested document IDs and metadata.

GET /api/report/{id}
- Returns the final report and resolved citations.

Configuration
-------------

Create a .env file (see .env.example). Required keys:
- OPENAI_API_KEY
- TAVILY_API_KEY

Optional settings include cache, retrieval, and critic thresholds.

Local development
-----------------

Prerequisites:
- Docker and Docker Compose

Run the stack:
```bash
make up
```

Stop the stack:
```bash
make down
```

Rebuild:
```bash
make rebuild
```

Ingestion CLI:
```bash
make ingest file=path/to/doc.pdf
make ingest-url url=https://example.com
```

Notes
-----

- The SSE stream is the source of truth for UI state.
- Tools never raise exceptions; they return structured observations.
- Analysis and synthesis only operate on approved sources.

License
-------

MIT. See LICENSE.
