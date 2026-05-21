from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import CRITIC_PASS_THRESHOLD, MAX_REVISIONS, get_llm
from app.graph.state import AgentState

_SYSTEM = """\
You are a research quality critic. Evaluate the draft report against the source claims.

Score the report on:
  1. Citation coverage  — every assertion has a [chunk_id] citation
  2. Factual accuracy   — claims are not distorted or overstated
  3. Completeness       — the research query is fully addressed
  4. Clarity            — the report is well-structured and readable

Output ONLY valid JSON:
{
  "score": 0.0-1.0,
  "feedback": "Concise, actionable list of issues to fix. Empty string if none."
}"""

_PROMPT_TEMPLATE = """\
Research query: {query}

Approved claims:
{claims_block}

Draft report:
{report}"""


def _format_claims(claims: list[dict]) -> str:
    return "\n".join(
        f"[{', '.join(c.get('chunk_ids', []))}] {c['text']}"
        for c in claims[:80]
    )


async def critic_node(state: AgentState) -> dict:
    llm = get_llm("critic")
    report_draft = state.get("report_draft", "")
    claims = state.get("claims", [])
    revision_count = state.get("revision_count", 0)

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=_PROMPT_TEMPLATE.format(
            query=state["query"],
            claims_block=_format_claims(claims) or "(none)",
            report=report_draft[:8_000],
        )),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        parsed = json.loads(raw)
        score = float(parsed.get("score", 0.5))
        feedback = parsed.get("feedback", "")
    except (json.JSONDecodeError, ValueError):
        score = 0.5
        feedback = raw

    update: dict = {
        "critic_score": score,
        "critic_feedback": feedback,
        "revision_count": revision_count + 1,
        "critic_scratchpad": (
            f"score={score:.2f} threshold={CRITIC_PASS_THRESHOLD} "
            f"revision={revision_count}"
        ),
    }

    # Track the highest-scoring draft so finalize_report can use it.
    best_so_far = state.get("best_critic_score") or 0.0
    if score >= best_so_far:
        update["best_report_draft"] = report_draft
        update["best_critic_score"] = score

    return update
