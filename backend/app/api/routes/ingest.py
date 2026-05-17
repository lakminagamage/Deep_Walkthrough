from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_and_store
from app.ingestion.loader import load_pdf, load_url

router = APIRouter()


@router.post("/ingest")
async def ingest_document(
    request: Request,
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
) -> dict:
    if not file and not url:
        raise HTTPException(status_code=400, detail="Provide 'file' or 'url'")

    memory = request.app.state.memory

    if file:
        suffix = ".pdf" if file.filename and file.filename.endswith(".pdf") else ".tmp"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        try:
            doc = await load_pdf(tmp_path)
        finally:
            os.unlink(tmp_path)
    else:
        try:
            doc = await load_url(url)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Failed to fetch URL: {exc}")

    chunks = chunk_document(doc)
    await embed_and_store(chunks, memory, session_id=session_id)

    return {
        "doc_id": doc.doc_id,
        "source_title": doc.source_title,
        "chunk_count": len(chunks),
    }


@router.get("/documents")
async def list_documents(request: Request) -> dict:
    """Return a summary of all doc IDs in the knowledge base."""
    memory = request.app.state.memory
    # Fetch a broad sample to gather distinct doc_ids
    results = await memory.query("documents", ".", top_k=200)
    seen: dict[str, dict] = {}
    for r in results:
        did = r["metadata"].get("doc_id", r["id"])
        if did not in seen:
            seen[did] = {
                "doc_id": did,
                "source_title": r["metadata"].get("source_title", ""),
                "source_url": r["metadata"].get("source_url", ""),
            }
    return {"documents": list(seen.values())}
