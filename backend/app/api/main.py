from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api.routes import ingest, report, research, session
from app.config import (
    CHROMA_HOST,
    CHROMA_PORT,
    LLM_CACHE_ENABLED,
    LLM_CACHE_TTL_SECONDS,
    REDIS_URL,
    SQLITE_PATH,
)
from app.memory.episodic import EpisodicMemory
from app.memory.long_term import LongTermMemory


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Memory clients ────────────────────────────────────────────────────────
    memory = LongTermMemory(host=CHROMA_HOST, port=CHROMA_PORT)
    episodic = EpisodicMemory(db_path=SQLITE_PATH)
    await episodic.init()

    # ── LLM response cache ────────────────────────────────────────────────────
    if LLM_CACHE_ENABLED:
        from langchain_core.globals import set_llm_cache

        from app.cache.llm_cache import RedisLLMCache
        set_llm_cache(RedisLLMCache(redis_url=REDIS_URL, ttl=LLM_CACHE_TTL_SECONDS))

    # ── Graph (checkpointer lives for the full app lifespan) ─────────────────
    from app.graph.graph import build_graph

    checkpointer_path = SQLITE_PATH.replace(".db", "_checkpointer.db")
    async with AsyncSqliteSaver.from_conn_string(checkpointer_path) as checkpointer:
        await checkpointer.setup()
        graph = build_graph(checkpointer)

        app.state.graph = graph
        app.state.memory = memory
        app.state.episodic = episodic
        app.state.session_queues: dict[str, asyncio.Queue] = {}

        yield
    # checkpointer connection closes on context exit


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Research Intelligence System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, prefix="/api")
app.include_router(ingest.router,   prefix="/api")
app.include_router(session.router,  prefix="/api")
app.include_router(report.router,   prefix="/api")
