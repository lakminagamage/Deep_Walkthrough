from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup


@dataclass
class RawDocument:
    source_url: str
    source_title: str
    content: str
    doc_id: str


async def load_pdf(file_path: str | Path) -> RawDocument:
    """Parse a PDF with pymupdf (sync) in a thread executor."""
    path = Path(file_path)

    def _parse() -> tuple[str, str]:
        import fitz  # pymupdf
        doc = fitz.open(str(path))
        title = doc.metadata.get("title") or path.stem
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return title, "\n\n".join(pages)

    title, content = await asyncio.get_event_loop().run_in_executor(None, _parse)
    return RawDocument(
        source_url=str(path.absolute()),
        source_title=title,
        content=content,
        doc_id=str(uuid.uuid4()),
    )


async def load_url(url: str) -> RawDocument:
    """Fetch a URL and extract plain text."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    content = soup.get_text(separator="\n", strip=True)

    return RawDocument(
        source_url=url,
        source_title=title,
        content=content,
        doc_id=str(uuid.uuid4()),
    )
