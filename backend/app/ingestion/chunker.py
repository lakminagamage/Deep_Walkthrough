from __future__ import annotations

import uuid
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.loader import RawDocument

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


@dataclass
class DocumentChunk:
    chunk_id: str
    content: str
    source_url: str
    source_title: str
    page_number: int | None
    doc_id: str
    char_count: int


def chunk_document(doc: RawDocument) -> list[DocumentChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    return [
        DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            content=text,
            source_url=doc.source_url,
            source_title=doc.source_title,
            page_number=None,
            doc_id=doc.doc_id,
            char_count=len(text),
        )
        for text in splitter.split_text(doc.content)
    ]
