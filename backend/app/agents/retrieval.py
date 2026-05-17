from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.config import MAX_RETRIEVAL_STEPS, MAX_TOOL_RETRIES, get_llm
from app.graph.state import AgentState, SourceCandidate
from app.tools.document import fetch_url
from app.tools.retrieval import make_vector_store_tool
from app.tools.search import web_search

_SYSTEM = """\
You are a research retrieval agent. Use tools to gather evidence for every sub-question.

Available tools:
  • query_vector_store — search the internal knowledge base (use FIRST for each sub-question)
  • web_search         — live web search via Tavily
  • fetch_url          — download and parse a specific URL

For each sub-question:
  1. Query the vector store.
  2. If coverage is thin, run a web search.
  3. Fetch individual URLs if a page looks highly relevant but you only have a snippet.

When you have adequate coverage across all sub-questions, output:
  DONE: <one-sentence summary of what was collected>

Do not call further tools after outputting DONE."""


def _parse_candidates(observation: str, seen_ids: set[str]) -> list[SourceCandidate]:
    """Extract SourceCandidate dicts from a SUCCESS observation."""
    if not observation.startswith("SUCCESS: "):
        return []
    try:
        data = json.loads(observation[len("SUCCESS: "):])
    except (json.JSONDecodeError, ValueError):
        return []

    candidates: list[SourceCandidate] = []
    if not isinstance(data, list):
        data = [data]

    for item in data:
        if not isinstance(item, dict):
            continue

        if "chunk_id" in item:
            cid = item["chunk_id"]
            if cid not in seen_ids:
                seen_ids.add(cid)
                candidates.append(item)  # type: ignore[arg-type]
        elif "url" in item:
            # Web search or fetch_url result — synthesise a SourceCandidate.
            cid = str(uuid.uuid4())
            seen_ids.add(cid)
            candidates.append({
                "chunk_id": cid,
                "content": item.get("snippet") or item.get("text") or "",
                "source_url": item.get("url", ""),
                "source_title": item.get("title", ""),
                "page_number": None,
                "credibility_score": 0.5,
                "approved": False,
            })

    return candidates


async def retrieval_node(state: AgentState) -> dict:
    vs_tool = make_vector_store_tool(state["session_id"])
    tools = [web_search, vs_tool, fetch_url]
    tool_map = {t.name: t for t in tools}
    llm = get_llm("retrieval").bind_tools(tools)

    plan = state["research_plan"]
    sub_questions = plan["sub_questions"] if plan else [state["query"]]

    sub_q_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(sub_questions))
    context = f"Main query: {state['query']}\n\nSub-questions:\n{sub_q_text}"

    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=context),
    ]

    scratchpad: list[str] = []
    all_candidates: list[SourceCandidate] = []
    seen_ids: set[str] = set()
    errors_in_state: list[dict] = list(state.get("errors", []))
    consecutive_errors = 0

    for step in range(MAX_RETRIEVAL_STEPS):
        response = await llm.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            scratchpad.append(f"[step {step + 1}] DONE — {response.content}")
            break

        for tc in response.tool_calls:
            name, args, call_id = tc["name"], tc["args"], tc["id"]
            scratchpad.append(f"[step {step + 1}] → {name}({json.dumps(args)})")

            tool_fn = tool_map.get(name)
            if tool_fn is None:
                observation = f"ERROR: unknown tool '{name}'"
                consecutive_errors += 1
            else:
                observation = await tool_fn.ainvoke(args)
                if observation.startswith("SUCCESS:"):
                    consecutive_errors = 0
                    new = _parse_candidates(observation, seen_ids)
                    all_candidates.extend(new)
                else:
                    consecutive_errors += 1
                    errors_in_state.append({
                        "agent": "retrieval",
                        "tool": name,
                        "error_message": observation,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            scratchpad.append(f"  ← {observation[:300]}")
            messages.append(ToolMessage(content=observation, tool_call_id=call_id))

        if consecutive_errors >= MAX_TOOL_RETRIES:
            scratchpad.append(f"[step {step + 1}] Max consecutive errors — aborting loop.")
            break

    return {
        "source_candidates": all_candidates,
        "retrieval_scratchpad": "\n".join(scratchpad),
        "errors": errors_in_state,
    }
