from __future__ import annotations

import asyncio

from langchain_core.tools import tool

from app.config import CHROMA_HOST, CHROMA_PORT, RETRIEVAL_TOP_K
from app.memory.long_term import LongTermMemory
from app.tools.base import ToolResult

# Module-level lazy singleton — shared across all tool calls in a process.
_memory: LongTermMemory | None = None


def _get_memory() -> LongTermMemory:
    global _memory
    if _memory is None:
        _memory = LongTermMemory(host=CHROMA_HOST, port=CHROMA_PORT)
    return _memory


def _rrf_fuse(
    dense: list[dict],
    sparse: list[dict],
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion of two ranked lists."""
    scores: dict[str, float] = {}
    meta: dict[str, dict] = {}

    for rank, doc in enumerate(dense):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        meta[doc_id] = doc

    for rank, doc in enumerate(sparse):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        meta.setdefault(doc_id, doc)

    return [meta[i] for i in sorted(scores, key=lambda x: scores[x], reverse=True)]


def _bm25_rank(query: str, corpus: list[dict], top_k: int) -> list[dict]:
    """In-process BM25 over the dense-retrieval corpus."""
    from rank_bm25 import BM25Okapi

    if not corpus:
        return []
    tokenized = [doc["document"].lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
    return [corpus[i] for i in ranked[:top_k]]


@tool
async def query_vector_store(
    query: str,
    document_ids: list[str] | None = None,
    top_k: int = RETRIEVAL_TOP_K,
) -> str:
    """Query the internal knowledge base using hybrid dense+BM25 retrieval with RRF fusion."""
    try:
        memory = _get_memory()

        # Dense retrieval — fetch 2× top_k to give BM25 a wider corpus to re-rank.
        dense = await memory.query("documents", query, top_k=top_k * 2)

        if document_ids:
            dense = [d for d in dense if d["metadata"].get("doc_id") in document_ids]

        # BM25 runs synchronously; offload to executor per design rule 4.1.
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
