from __future__ import annotations

import asyncio

from langchain_core.tools import tool

from app.config import CHROMA_HOST, CHROMA_PORT, RETRIEVAL_TOP_K
from app.memory.long_term import LongTermMemory
from app.tools.base import ToolResult

_memory: LongTermMemory | None = None


def _get_memory() -> LongTermMemory:
    global _memory
    if _memory is None:
        _memory = LongTermMemory(host=CHROMA_HOST, port=CHROMA_PORT)
    return _memory


def _rrf_fuse(dense: list[dict], sparse: list[dict], k: int = 60) -> list[dict]:
    scores: dict[str, float] = {}
    meta: dict[str, dict] = {}
    for rank, doc in enumerate(dense):
        did = doc["id"]
        scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank + 1)
        meta[did] = doc
    for rank, doc in enumerate(sparse):
        did = doc["id"]
        scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank + 1)
        meta.setdefault(did, doc)
    return [meta[i] for i in sorted(scores, key=lambda x: scores[x], reverse=True)]


def _bm25_rank(query: str, corpus: list[dict], top_k: int) -> list[dict]:
    from rank_bm25 import BM25Okapi
    if not corpus:
        return []
    tokenized = [doc["document"].lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
    return [corpus[i] for i in ranked[:top_k]]


def make_vector_store_tool(session_id: str):
    """Return a query_vector_store tool scoped to a specific session."""

    @tool
    async def query_vector_store(query: str, top_k: int = RETRIEVAL_TOP_K) -> str:
        """Query the internal knowledge base using hybrid dense+BM25 retrieval with RRF fusion."""
        try:
            memory = _get_memory()
            dense = await memory.query(
                "documents", query, top_k=top_k * 2, session_id=session_id
            )
            loop = asyncio.get_event_loop()
            sparse = await loop.run_in_executor(None, _bm25_rank, query, dense, top_k)
            fused = _rrf_fuse(dense, sparse)[:top_k]
            candidates = [
                {
                    "chunk_id": doc["id"],
                    "content": doc["document"],
                    "source_url": doc["metadata"].get("source_url", ""),
                    "source_title": doc["metadata"].get("source_title", ""),
                    "page_number": doc["metadata"].get("page_number"),
                    "credibility_score": 0.5,
                    "approved": False,
                }
                for doc in fused
            ]
            return ToolResult(success=True, data=candidates).to_observation()
        except Exception as exc:
            return ToolResult(success=False, error_message=str(exc)).to_observation()

    return query_vector_store
