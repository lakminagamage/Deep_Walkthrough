from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import (
    CRITIC_PASS_THRESHOLD,
    MAX_RETRIEVAL_ATTEMPTS_PER_SUBQUESTION,
    MAX_REVISIONS,
    MIN_SOURCE_CREDIBILITY,
    MIN_SOURCES_PER_SUBQUESTION,
    get_llm,
)
from app.graph.state import AgentState, ResearchPlan, SupervisorDecision

# ── Plan node 

_PLAN_SYSTEM = """\
You are a research planning agent. Decompose the user's research question into a structured
plan of focused sub-questions that can be investigated independently.

Reason step-by-step before producing the plan:
1. Understand what a complete, well-cited answer requires.
2. Identify distinct aspects, dimensions, or sub-topics.
3. Order sub-questions from foundational to complex.
4. Aim for 3–6 sub-questions that together fully address the main query.

Output ONLY valid JSON (no markdown fences):
{
  "reasoning": "<your step-by-step thinking>",
  "sub_questions": ["question 1", "question 2", ...]
}"""


async def supervisor_plan_node(state: AgentState) -> dict:
    llm = get_llm("supervisor")
    query = state["query"]

    response = await llm.ainvoke([
        SystemMessage(content=_PLAN_SYSTEM),
        HumanMessage(content=f"Research query: {query}"),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        parsed = json.loads(raw)
        reasoning = parsed.get("reasoning", "")
        sub_questions: list[str] = parsed.get("sub_questions", [query])
    except json.JSONDecodeError:
        reasoning = raw
        sub_questions = [query]

    plan: ResearchPlan = {"sub_questions": sub_questions, "approved": False}

    return {
        "research_plan": plan,
        "supervisor_scratchpad": reasoning,
        "supervisor_decisions": [],
        "current_supervisor_instruction": None,
        "retrieval_attempts": {},
        "last_retrieval_new_chunk_count": -1,
    }


# ── Route node ───

_ROUTE_SYSTEM = """\
You are a research orchestration supervisor. Analyse the current pipeline state and make
a routing decision about what happens next.

Reason step-by-step through the evidence before deciding. Then output ONLY valid JSON
(no markdown fences):
{
  "reasoning": "<your step-by-step analysis>",
  "next": "<exactly one of the allowed values for this stage>",
  "instruction": "<directive for the next agent, or null>"
}"""


def _determine_stage(
    state: AgentState,
) -> Literal["post_sources", "post_analysis", "post_critic"]:
    if state.get("critic_score") is not None:
        return "post_critic"
    if state.get("claims"):
        return "post_analysis"
    return "post_sources"


def _build_post_sources_context(state: AgentState) -> str:
    approved = state.get("approved_sources", [])
    plan = state.get("research_plan")
    sub_questions = plan["sub_questions"] if plan else [state["query"]]

    source_lines = []
    for s in approved:
        source_lines.append(
            f"  [{s['chunk_id'][:8]}] \"{s['source_title']}\" "
            f"credibility={s['credibility_score']:.2f} | {s['content'][:120]}..."
        )

    avg_cred = (
        sum(s["credibility_score"] for s in approved) / len(approved)
        if approved else 0.0
    )
    avg_per_sq = len(approved) / len(sub_questions) if sub_questions else 0.0
    all_low_cred = all(s["credibility_score"] < MIN_SOURCE_CREDIBILITY for s in approved) if approved else True

    return (
        f"Stage: post_sources\n\n"
        f"Sub-questions ({len(sub_questions)}):\n"
        + "\n".join(f"  {i+1}. {q}" for i, q in enumerate(sub_questions))
        + f"\n\nApproved sources: {len(approved)} total | "
        f"avg credibility={avg_cred:.2f} | avg per sub-question={avg_per_sq:.1f}\n"
        + ("\n".join(source_lines) if source_lines else "  (none)")
        + f"\n\nThresholds: MIN_SOURCES_PER_SUBQUESTION={MIN_SOURCES_PER_SUBQUESTION}, "
        f"MIN_SOURCE_CREDIBILITY={MIN_SOURCE_CREDIBILITY}\n"
        f"All sources below credibility threshold: {all_low_cred}\n\n"
        f"Allowed next values: \"analysis\" or \"retrieval\"\n"
        f"Route to \"retrieval\" if:\n"
        f"  - avg sources per sub-question < {MIN_SOURCES_PER_SUBQUESTION} "
        f"(currently {avg_per_sq:.1f}), OR\n"
        f"  - all credibility scores below {MIN_SOURCE_CREDIBILITY}, OR\n"
        f"  - a critical sub-question has zero coverage based on source content\n"
        f"If routing to \"retrieval\": instruction MUST name the under-covered sub-questions "
        f"and specify what kind of sources to seek.\n"
        f"If routing to \"analysis\": set instruction to null."
    )


def _prior_decisions_text(state: AgentState) -> str:
    decisions = state.get("supervisor_decisions", [])
    if not decisions:
        return ""
    lines = [
        f"  #{i+1}: {d['stage']} → {d['next']} | {d['reasoning'][:120]}..."
        for i, d in enumerate(decisions)
    ]
    retrieval_count = sum(1 for d in decisions if d["next"] == "retrieval")
    warning = (
        f"\n  *** You have already routed to retrieval {retrieval_count} time(s). "
        "If you have routed to retrieval more than once for the same gaps, "
        "you MUST route to synthesis instead — repeated retrieval for the same gaps "
        "means the information is not available. Acknowledge gaps in the report. ***"
        if retrieval_count > 0 else ""
    )
    return (
        "\nYour prior routing decisions this session:\n"
        + "\n".join(lines)
        + warning
    )


def _build_post_analysis_context(state: AgentState) -> str:
    claims = state.get("claims", [])
    gaps = state.get("analysis_gaps", [])
    revision_count = state.get("revision_count", 0)
    new_chunks = state.get("last_retrieval_new_chunk_count", -1)
    attempts = state.get("retrieval_attempts", {})
    max_attempts = max(attempts.values(), default=0)

    confidences = [c["confidence"] for c in claims]
    high = sum(1 for c in confidences if c >= 0.7)
    mid = sum(1 for c in confidences if 0.4 <= c < 0.7)
    low = sum(1 for c in confidences if c < 0.4)

    gap_lines = "\n".join(f"  - {g}" for g in gaps) if gaps else "  (none)"

    return (
        f"Stage: post_analysis\n\n"
        f"Claims extracted: {len(claims)} | "
        f"confidence distribution: high={high} mid={mid} low={low}\n"
        f"Coverage gaps ({len(gaps)}):\n{gap_lines}\n\n"
        f"Current revision count: {revision_count} / {MAX_REVISIONS}\n"
        f"Retrieval attempts per sub-question: {dict(attempts)} "
        f"(max={max_attempts}, ceiling={MAX_RETRIEVAL_ATTEMPTS_PER_SUBQUESTION})\n"
        f"New chunks found in last retrieval pass: {new_chunks} "
        f"({'no new sources found — looping is futile' if new_chunks == 0 else 'new sources available'})\n\n"
        f"Allowed next values: \"synthesis\" or \"retrieval\"\n"
        f"Route to \"retrieval\" ONLY if: gaps are critical (not minor) AND "
        f"revision_count ({revision_count}) < MAX_REVISIONS ({MAX_REVISIONS}) AND "
        f"max retrieval attempts < {MAX_RETRIEVAL_ATTEMPTS_PER_SUBQUESTION} AND "
        f"last retrieval found new chunks (new_chunks > 0).\n"
        f"Otherwise route to \"synthesis\".\n"
        f"If routing to \"synthesis\": instruction should highlight which gaps to acknowledge "
        f"explicitly in the report rather than fabricate coverage for.\n"
        f"If routing to \"retrieval\": instruction must specify what information to find."
        + _prior_decisions_text(state)
    )


def _build_post_critic_context(state: AgentState) -> str:
    score = state.get("critic_score", 0.0)
    feedback = state.get("critic_feedback", "")
    revision_count = state.get("revision_count", 0)

    return (
        f"Stage: post_critic\n\n"
        f"Critic score: {score:.2f} (pass threshold: {CRITIC_PASS_THRESHOLD})\n"
        f"Revision count: {revision_count} / {MAX_REVISIONS}\n"
        f"Critic feedback:\n{feedback or '(none)'}\n\n"
        f"Allowed next values: \"synthesis\" or \"end\"\n"
        f"Route to \"synthesis\" if: score < {CRITIC_PASS_THRESHOLD} AND "
        f"revision_count ({revision_count}) < MAX_REVISIONS ({MAX_REVISIONS}).\n"
        f"Route to \"end\" otherwise (score passed or revision limit reached).\n"
        f"If routing to \"synthesis\": identify THE SINGLE most impactful issue from the "
        f"critic feedback and write an instruction that targets ONLY that one issue. "
        f"Do not ask Synthesis to fix multiple things at once — over-correction degrades quality. "
        f"Start the instruction with: \"Focus only on: \"\n"
        f"If routing to \"end\": set instruction to null."
    )


async def supervisor_route_node(state: AgentState) -> dict:
    stage = _determine_stage(state)

    # Hard overrides for post_analysis — skip LLM when looping is futile.
    if stage == "post_analysis":
        new_chunks = state.get("last_retrieval_new_chunk_count", -1)
        attempts = state.get("retrieval_attempts", {})
        max_attempts = max(attempts.values(), default=0)

        forced_reason: str | None = None
        if new_chunks == 0:
            forced_reason = (
                "Hard override: last retrieval pass found 0 new chunks — "
                "repeating retrieval is futile. Routing to synthesis."
            )
        elif max_attempts >= MAX_RETRIEVAL_ATTEMPTS_PER_SUBQUESTION:
            forced_reason = (
                f"Hard override: retrieval attempt ceiling reached "
                f"({max_attempts}/{MAX_RETRIEVAL_ATTEMPTS_PER_SUBQUESTION}). "
                "Routing to synthesis."
            )

        if forced_reason is not None:
            decision: SupervisorDecision = {
                "stage": stage,
                "next": "synthesis",
                "reasoning": forced_reason,
                "instruction": (
                    "Acknowledge any coverage gaps explicitly in the report "
                    "rather than fabricating information."
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            existing_decisions = list(state.get("supervisor_decisions", []))
            existing_decisions.append(decision)
            return {
                "supervisor_decisions": existing_decisions,
                "current_supervisor_instruction": decision["instruction"],
                "supervisor_scratchpad": (
                    state.get("supervisor_scratchpad", "")
                    + f"\n\n--- {stage} (forced) ---\n"
                    + forced_reason
                ),
            }

    if stage == "post_sources":
        context = _build_post_sources_context(state)
    elif stage == "post_analysis":
        context = _build_post_analysis_context(state)
    else:
        context = _build_post_critic_context(state)

    llm = get_llm("supervisor")
    response = await llm.ainvoke([
        SystemMessage(content=_ROUTE_SYSTEM),
        HumanMessage(content=context),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        parsed = json.loads(raw)
        reasoning: str = parsed.get("reasoning", "")
        next_step: str = parsed.get("next", "analysis")
        instruction: str | None = parsed.get("instruction") or None
    except (json.JSONDecodeError, ValueError):
        reasoning = raw
        # Safe fallbacks per stage
        next_step = (
            "analysis" if stage == "post_sources"
            else "synthesis" if stage == "post_analysis"
            else "end"
        )
        instruction = None

    llm_decision: SupervisorDecision = {
        "stage": stage,
        "next": next_step,  # type: ignore[assignment]
        "reasoning": reasoning,
        "instruction": instruction,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    existing_decisions = list(state.get("supervisor_decisions", []))
    existing_decisions.append(llm_decision)

    existing_scratchpad = state.get("supervisor_scratchpad", "")
    new_scratchpad = (
        existing_scratchpad
        + f"\n\n--- {stage} ---\n"
        + reasoning
    )

    result: dict = {
        "supervisor_decisions": existing_decisions,
        "current_supervisor_instruction": llm_decision["instruction"],
        "supervisor_scratchpad": new_scratchpad,
    }

    # Bug 3: When looping back to retrieval from post_analysis, clear claims so
    # _determine_stage returns "post_sources" after the next HITL gate, forcing
    # Analysis to re-run and refresh claims/gaps against the newly approved sources.
    if stage == "post_analysis" and llm_decision["next"] == "retrieval":
        result["claims"] = []
        result["analysis_gaps"] = []

    return result
