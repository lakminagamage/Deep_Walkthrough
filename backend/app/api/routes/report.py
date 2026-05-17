from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

_CHUNK_ID_RE = re.compile(r"\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]")


@router.get("/report/{session_id}")
async def get_report(session_id: str, request: Request) -> dict:
    graph = request.app.state.graph
    memory = request.app.state.memory

    config = {"configurable": {"thread_id": session_id}}
    state = await graph.aget_state(config)

    if not state or not (state.values or {}).get("report_final"):
        raise HTTPException(status_code=404, detail="Report not found or not yet complete")

    vals = state.values
    report = vals["report_final"]
    report_id = vals.get("report_id", session_id)

    # Resolve chunk_id citations embedded as [uuid] markers.
    chunk_ids = list(set(_CHUNK_ID_RE.findall(report)))
    citations: dict[str, dict] = {}
    if chunk_ids:
        chunks = await memory.get_by_ids("documents", chunk_ids)
        for chunk in chunks:
            citations[chunk["id"]] = {
                "source_url":   chunk["metadata"].get("source_url", ""),
                "source_title": chunk["metadata"].get("source_title", ""),
                "page_number":  chunk["metadata"].get("page_number"),
                "chunk_text":   chunk["document"][:400],
            }

    return {
        "report_id":    report_id,
        "session_id":   session_id,
        "query":        vals.get("query", ""),
        "report_final": report,
        "citations":    citations,
        "critic_score": vals.get("critic_score"),
        "revision_count": vals.get("revision_count", 0),
    }
