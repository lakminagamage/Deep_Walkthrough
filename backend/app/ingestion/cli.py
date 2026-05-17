"""CLI entry point: python -m app.ingestion.cli --file path/to/doc.pdf"""
from __future__ import annotations

import argparse
import asyncio

from app.config import CHROMA_HOST, CHROMA_PORT
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_and_store
from app.ingestion.loader import load_pdf, load_url
from app.memory.long_term import LongTermMemory


async def run(file: str | None, url: str | None) -> None:
    memory = LongTermMemory(host=CHROMA_HOST, port=CHROMA_PORT)

    if file:
        print(f"Loading PDF: {file}")
        doc = await load_pdf(file)
    elif url:
        print(f"Loading URL: {url}")
        doc = await load_url(url)
    else:
        raise ValueError("Provide --file or --url")

    chunks = chunk_document(doc)
    print(f"Chunked into {len(chunks)} pieces  (doc_id={doc.doc_id})")

    await embed_and_store(chunks, memory)
    print(f"Stored {len(chunks)} chunks in ChromaDB  (doc_id={doc.doc_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a document into the research agent")
    parser.add_argument("--file", help="Path to a PDF file")
    parser.add_argument("--url", help="URL to fetch and ingest")
    args = parser.parse_args()
    asyncio.run(run(args.file, args.url))


if __name__ == "__main__":
    main()
