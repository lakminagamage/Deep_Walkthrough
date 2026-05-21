from __future__ import annotations

import json
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_llm
from app.graph.state import AgentState, Claim
from app.tools.analysis import extract_claims

_GAPS_SYSTEM = """\
You are a research analyst. Given a list of factual claims and the original sub-questions,
identify topics that are NOT adequately covered by the claims.

Output ONLY valid JSON:
{"gaps": ["topic 1", "topic 2", ...]}
Return an empty list if coverage is sufficient."""


async def analysis_node(state: AgentState) -> dict:
    instruction = state.get("current_supervisor_instruction")
    state_update: dict = {"current_supervisor_instruction": None}

    approved_sources = state.get("approved_sources", [])
    errors_in_state: list[dict] = list(state.get("errors", []))
    scratchpad: list[str] = []
    if instruction:
        scratchpad.append(f"[supervisor directive] {instruction}")
    all_claims: list[Claim] = []

    # ── Per-source: score credibility + extract claims ──

    for source in approved_sources:
        chunk_id = source["chunk_id"]

        # Extract claims.
        claims_obs = await extract_claims.ainvoke({
            "chunk": source["content"],
            "chunk_id": chunk_id,
        })

        if claims_obs.startswith("SUCCESS: "):
            try:
                claim_list = json.loads(claims_obs[len("SUCCESS: "):])
                for c in claim_list:
                    # Weight confidence by source credibility.
                    c["confidence"] = round(
                        c["confidence"] * source["credibility_score"], 3
                    )
                    all_claims.append(c)
                scratchpad.append(
                    f"[claims] chunk={chunk_id[:8]} → {len(claim_list)} claims extracted"
                )
            except (json.JSONDecodeError, TypeError):
                errors_in_state.append({
                    "agent": "analysis",
                    "tool": "extract_claims",
                    "error_message": "Failed to parse claims JSON",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        else:
            errors_in_state.append({
                "agent": "analysis",
                "tool": "extract_claims",
                "error_message": claims_obs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    # ── Gap analysis via LLM 

    plan = state.get("research_plan")
    sub_questions = plan["sub_questions"] if plan else [state["query"]]
    claims_summary = "\n".join(f"- {c['text']}" for c in all_claims[:60])

    instruction_suffix = f"\n\nDirective from Supervisor: {instruction}" if instruction else ""
    llm = get_llm("analysis")
    gap_response = await llm.ainvoke([
        SystemMessage(content=_GAPS_SYSTEM),
        HumanMessage(
            content=(
                f"Sub-questions:\n{chr(10).join(sub_questions)}\n\n"
                f"Extracted claims (up to 60):\n{claims_summary or '(none)'}"
                + instruction_suffix
            )
        ),
    ])

    raw = gap_response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        gaps: list[str] = json.loads(raw).get("gaps", [])
    except json.JSONDecodeError:
        gaps = []

    scratchpad.append(f"[gaps] identified {len(gaps)} coverage gap(s)")

    return {
        **state_update,
        "claims": all_claims,
        "analysis_gaps": gaps,
        "approved_sources": approved_sources,  # credibility scores updated in-place
        "analysis_scratchpad": "\n".join(scratchpad),
        "errors": errors_in_state,
    }
