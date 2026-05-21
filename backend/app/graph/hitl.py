from __future__ import annotations

from langgraph.graph import END
from langgraph.types import Command, interrupt

from app.graph.state import AgentState, ResearchPlan, SourceCandidate


# ── Gate 1 — Plan Approval ──

async def hitl_plan_approval_node(state: AgentState) -> Command:
    """Pause graph and surface the research plan for human review.

    Resumes when POST /api/session/{id}/resume sends:
      {"action": "approve"}
      {"action": "edit", "plan": {"sub_questions": [...], "approved": false}}
      {"action": "reject"}
    """
    plan = state["research_plan"]

    decision: dict = interrupt({
        "gate": "plan",
        "plan": plan,
        "session_id": state["session_id"],
    })

    action = decision.get("action", "approve")

    if action == "reject":
        return Command(goto=END)

    approved_plan: ResearchPlan = decision.get("plan", plan)
    approved_plan["approved"] = True

    return Command(
        goto="retrieval_agent",
        update={
            "research_plan": approved_plan,
            "hitl_plan_approved": True,
        },
    )


# ── Gate 2 — Source Approval 

async def hitl_source_approval_node(state: AgentState) -> Command:
    """Pause graph and surface retrieved source candidates for human review.

    Resumes when POST /api/session/{id}/resume sends:
      {"approved_chunk_ids": ["id1", "id2", ...]}
    """
    candidates: list[SourceCandidate] = state["source_candidates"]

    decision: dict = interrupt({
        "gate": "sources",
        "sources": candidates,
        "session_id": state["session_id"],
    })

    approved_ids: set[str] = set(decision.get("approved_chunk_ids", []))
    newly_approved: list[SourceCandidate] = [
        {**s, "approved": True}
        for s in candidates
        if s["chunk_id"] in approved_ids
    ]

    # Merge with previously approved sources so Analysis always sees the full set.
    existing: list[SourceCandidate] = state.get("approved_sources", [])
    existing_ids: set[str] = {s["chunk_id"] for s in existing}
    merged: list[SourceCandidate] = existing + [
        s for s in newly_approved if s["chunk_id"] not in existing_ids
    ]

    return Command(
        goto="supervisor_route",
        update={
            "approved_sources": merged,
            "hitl_sources_approved": True,
        },
    )
