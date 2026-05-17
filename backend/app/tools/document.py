from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool

from app.tools.base import ToolResult

# Cap fetched text to avoid flooding the context window.
_MAX_CHARS = 8_000


@tool
async def fetch_url(url: str) -> str:
    """Fetch a URL and return its cleaned plain-text content."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

        return ToolResult(
            success=True,
            data={
                "url": url,
                "title": title,
                "text": text[:_MAX_CHARS],
                "char_count": len(text),
            },
        ).to_observation()
    except Exception as exc:
        return ToolResult(success=False, error_message=str(exc)).to_observation()
