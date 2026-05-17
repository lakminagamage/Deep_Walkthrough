from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.config import get_llm
from app.tools.base import ToolResult

# ── Credibility heuristics ────────────────────────────────────────────────────

_DOMAIN_SCORES: dict[str, tuple[float, str]] = {
    ".gov":                       (0.90, ".gov domain"),
    ".edu":                       (0.90, ".edu domain"),
    "pubmed.ncbi.nlm.nih.gov":    (0.92, "PubMed"),
    "arxiv.org":                  (0.85, "arXiv"),
    "wikipedia.org":              (0.80, "Wikipedia"),
    "reuters.com":                (0.80, "Reuters"),
    "apnews.com":                 (0.80, "AP News"),
    "bbc.com":                    (0.75, "BBC"),
    "nytimes.com":                (0.75, "NYT"),
    "theguardian.com":            (0.75, "The Guardian"),
}

_EXTRACT_SYSTEM = (
    "You are a fact-extraction assistant. "
    "Output ONLY valid JSON — no markdown fences, no prose."
)

_EXTRACT_PROMPT = """\
Extract every verifiable factual claim from the chunk below.
Return JSON: {{"claims": [{{"text": "...", "confidence": 0.9}}, ...]}}
Omit opinions, speculation, and meta-commentary.

Chunk:
{chunk}"""


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
async def extract_claims(chunk: str, chunk_id: str) -> str:
    """Extract factual claims from a text chunk using an LLM call."""
    try:
        llm = get_llm("analysis")
        response = await llm.ainvoke([
            SystemMessage(content=_EXTRACT_SYSTEM),
            HumanMessage(content=_EXTRACT_PROMPT.format(chunk=chunk[:4_000])),
        ])
        raw = response.content.strip()
        parsed = json.loads(raw)
        claims = [
            {
                "text": c["text"],
                "chunk_ids": [chunk_id],
                "confidence": float(c.get("confidence", 0.7)),
            }
            for c in parsed.get("claims", [])
        ]
        return ToolResult(success=True, data=claims).to_observation()
    except Exception as exc:
        return ToolResult(success=False, error_message=str(exc)).to_observation()


@tool
async def score_credibility(url: str) -> str:
    """Score a source URL's credibility using domain heuristics (0.0–1.0)."""
    try:
        url_lower = url.lower()
        score, reason = 0.5, "Unknown domain"

        for pattern, (s, label) in _DOMAIN_SCORES.items():
            if pattern in url_lower:
                score, reason = s, f"Matched: {label}"
                break
        else:
            if url_lower.startswith("https://"):
                score, reason = 0.55, "HTTPS but unknown domain"

        return ToolResult(
            success=True,
            data={"url": url, "score": score, "reason": reason},
        ).to_observation()
    except Exception as exc:
        return ToolResult(success=False, error_message=str(exc)).to_observation()
