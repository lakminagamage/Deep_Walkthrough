from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.config import get_llm
from app.tools.base import ToolResult

# ── Credibility heuristics ──

_DOMAIN_SCORES: dict[str, tuple[float, str]] = {
    # ── Government & intergovernmental ───
    ".gov":                           (0.90, ".gov domain"),
    ".mil":                           (0.88, ".mil domain"),
    "who.int":                        (0.90, "WHO"),
    "un.org":                         (0.88, "United Nations"),
    "worldbank.org":                  (0.87, "World Bank"),
    "imf.org":                        (0.87, "IMF"),
    "oecd.org":                       (0.87, "OECD"),
    "europa.eu":                      (0.87, "EU"),

    # ── Academic & research ─
    ".edu":                           (0.90, ".edu domain"),
    ".ac.uk":                         (0.90, ".ac.uk domain"),
    "pubmed.ncbi.nlm.nih.gov":        (0.95, "PubMed"),
    "arxiv.org":                      (0.85, "arXiv"),
    "scholar.google.com":             (0.85, "Google Scholar"),
    "semanticscholar.org":            (0.85, "Semantic Scholar"),
    "researchgate.net":               (0.80, "ResearchGate"),
    "ssrn.com":                       (0.82, "SSRN"),
    "jstor.org":                      (0.88, "JSTOR"),
    "springer.com":                   (0.85, "Springer"),
    "nature.com":                     (0.92, "Nature"),
    "science.org":                    (0.92, "Science"),
    "cell.com":                       (0.91, "Cell"),
    "thelancet.com":                  (0.91, "The Lancet"),
    "nejm.org":                       (0.93, "NEJM"),
    "jamanetwork.com":                (0.91, "JAMA"),
    "bmj.com":                        (0.90, "BMJ"),
    "plos.org":                       (0.85, "PLOS"),
    "frontiersin.org":                (0.82, "Frontiers"),
    "acm.org":                        (0.87, "ACM"),
    "ieee.org":                       (0.88, "IEEE"),
    "ieeexplore.ieee.org":            (0.88, "IEEE Xplore"),
    "dl.acm.org":                     (0.87, "ACM Digital Library"),
    "openreview.net":                 (0.83, "OpenReview"),
    "proceedings.mlr.press":          (0.86, "PMLR"),
    "neurips.cc":                     (0.87, "NeurIPS"),
    "huggingface.co":                 (0.80, "Hugging Face"),

    # ── Encyclopedic & reference ────
    "wikipedia.org":                  (0.80, "Wikipedia"),
    "britannica.com":                 (0.82, "Britannica"),
    "merriam-webster.com":            (0.80, "Merriam-Webster"),

    # ── News & journalism ───
    "reuters.com":                    (0.85, "Reuters"),
    "apnews.com":                     (0.85, "AP News"),
    "bbc.com":                        (0.82, "BBC"),
    "bbc.co.uk":                      (0.82, "BBC"),
    "nytimes.com":                    (0.80, "NYT"),
    "theguardian.com":                (0.80, "The Guardian"),
    "washingtonpost.com":             (0.79, "Washington Post"),
    "wsj.com":                        (0.80, "Wall Street Journal"),
    "ft.com":                         (0.82, "Financial Times"),
    "economist.com":                  (0.82, "The Economist"),
    "bloomberg.com":                  (0.80, "Bloomberg"),
    "npr.org":                        (0.80, "NPR"),
    "pbs.org":                        (0.80, "PBS"),
    "theatlantic.com":                (0.77, "The Atlantic"),
    "newyorker.com":                  (0.78, "The New Yorker"),
    "politico.com":                   (0.75, "Politico"),
    "foreignaffairs.com":             (0.82, "Foreign Affairs"),
    "foreignpolicy.com":              (0.80, "Foreign Policy"),

    # ── Tech & science media 
    "techcrunch.com":                 (0.70, "TechCrunch"),
    "wired.com":                      (0.72, "Wired"),
    "arstechnica.com":                (0.74, "Ars Technica"),
    "theverge.com":                   (0.70, "The Verge"),
    "scientificamerican.com":         (0.84, "Scientific American"),
    "newscientist.com":               (0.80, "New Scientist"),
    "technologyreview.com":           (0.82, "MIT Technology Review"),
    "spectrum.ieee.org":              (0.84, "IEEE Spectrum"),

    # ── Think tanks & policy 
    "brookings.edu":                  (0.85, "Brookings"),
    "rand.org":                       (0.86, "RAND"),
    "pewresearch.org":                (0.85, "Pew Research"),
    "cfr.org":                        (0.84, "CFR"),
    "csis.org":                       (0.83, "CSIS"),
    "chathamhouse.org":               (0.84, "Chatham House"),

    # ── Open data & standards ──
    "github.com":                     (0.68, "GitHub"),
    "stackoverflow.com":              (0.68, "Stack Overflow"),
    "docs.python.org":                (0.88, "Python Docs"),
    "developer.mozilla.org":          (0.85, "MDN"),
    "w3.org":                         (0.88, "W3C"),
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


# ── Tools ─

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
