from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.graph.state import AgentState


async def finalize_report_node(state: AgentState) -> dict:
    # Prefer the highest-scoring draft; fall back to the most recent draft.
    best_draft = state.get("best_report_draft") or state.get("report_draft")

    if not best_draft:
        return {
            "errors": list(state.get("errors", [])) + [{
                "agent": "finalize",
                "tool": "finalize",
                "error_message": "Pipeline ended with no report draft",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }]
        }

    report_id = state.get("report_id") or str(uuid.uuid4())
    return {
        "report_final": best_draft,
        "report_id": report_id,
    }
