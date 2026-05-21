from __future__ import annotations

import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_llm
from app.graph.state import AgentState

_SYSTEM = """\
You are a research synthesis agent. Write a comprehensive, well-structured markdown report
that answers the research query based solely on the provided claims.

Rules:
  • Every paragraph must cite at least one claim using inline markers: [chunk_id]
  • Do NOT assert anything that is not supported by a listed claim.
  • Use standard markdown: # headings, ## sub-headings, bullet lists, bold for key terms.
  • End with a ## Summary section.
  • If critic feedback is provided, address each point explicitly.

Citation format: [chunk_id] — use the exact chunk_id strings provided."""

_CLAIMS_TEMPLATE = """\
Research query: {query}

Claims (each has chunk_ids for citation):
{claims_block}

{critic_section}Write the report now."""


def _format_claims(claims: list[dict]) -> str:
    lines = []
    for c in claims:
        ids = ", ".join(c.get("chunk_ids", []))
        lines.append(f"[{ids}] (confidence={c.get('confidence', 0):.2f}) {c['text']}")
    return "\n".join(lines)


async def synthesis_node(state: AgentState) -> dict:
    instruction = state.get("current_supervisor_instruction")
    state_update: dict = {"current_supervisor_instruction": None}

    llm = get_llm("synthesis")
    claims = state.get("claims", [])
    query = state["query"]
    feedback = state.get("critic_feedback")

    critic_section = ""
    if feedback:
        critic_section = f"Critic feedback to address in this revision:\n{feedback}\n\n"

    prompt_suffix = f"\n\nDirective from Supervisor: {instruction}" if instruction else ""
    prompt = _CLAIMS_TEMPLATE.format(
        query=query,
        claims_block=_format_claims(claims) or "(no claims available)",
        critic_section=critic_section,
    ) + prompt_suffix

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=prompt),
    ])

    report_draft = response.content.strip()
    report_id = str(uuid.uuid4())

    return {
        **state_update,
        "report_draft": report_draft,
        "report_id": report_id,
        "synthesis_scratchpad": (
            (f"[supervisor directive] {instruction}\n" if instruction else "")
            + f"Generated report ({len(report_draft)} chars, "
            f"revision={state.get('revision_count', 0)})"
        ),
    }
