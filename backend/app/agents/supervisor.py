from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_llm
from app.graph.state import AgentState, ResearchPlan

_SYSTEM = """\
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


async def supervisor_node(state: AgentState) -> dict:
    llm = get_llm("supervisor")
    query = state["query"]

    response = await llm.ainvoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"Research query: {query}"),
    ])

    raw = response.content.strip()
    # Strip accidental markdown fences from the LLM response.
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
    }
