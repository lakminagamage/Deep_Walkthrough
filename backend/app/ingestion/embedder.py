from __future__ import annotations

from app.ingestion.chunker import DocumentChunk
from app.memory.long_term import LongTermMemory


async def embed_and_store(chunks: list[DocumentChunk], memory: LongTermMemory) -> None:
    """Embed chunks via the LongTermMemory client and persist to ChromaDB."""
    documents = [
        {
            "chunk_id": c.chunk_id,
            "content": c.content,
            "source_url": c.source_url,
            "source_title": c.source_title,
            "page_number": c.page_number,
            "doc_id": c.doc_id,
            "char_count": c.char_count,
        }
        for c in chunks
    ]
    await memory.store("documents", documents)
