from __future__ import annotations

import os

from langchain_core.tools import tool

from app.tools.base import ToolResult


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for current information using the Tavily API."""
    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        response = await client.search(query, max_results=max_results)
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "score": r.get("score", 0.0),
            }
            for r in response.get("results", [])
        ]
        return ToolResult(success=True, data=results).to_observation()
    except Exception as exc:
        return ToolResult(success=False, error_message=str(exc)).to_observation()
