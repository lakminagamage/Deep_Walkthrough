from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.config import MAX_RETRIEVAL_STEPS, MAX_TOOL_RETRIES, get_llm
from app.graph.state import AgentState, SourceCandidate
from app.tools.analysis import score_credibility
from app.tools.document import fetch_url
from app.tools.retrieval import make_vector_store_tool
from app.tools.search import web_search

_SYSTEM_WITH_VS = """\
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

_SYSTEM_WEB_ONLY = """\
You are a research retrieval agent. Use tools to gather evidence for every sub-question.

Available tools:
  • web_search — live web search via Tavily
  • fetch_url  — download and parse a specific URL

For each sub-question:
  1. Run a web search.
  2. Fetch individual URLs if a page looks highly relevant but you only have a snippet.

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
    instruction = state.get("current_supervisor_instruction")
    state_update: dict = {"current_supervisor_instruction": None}

    has_documents = bool(state.get("document_ids"))
    if has_documents:
        vs_tool = make_vector_store_tool(state["session_id"])
        tools = [web_search, vs_tool, fetch_url]
        system_prompt = _SYSTEM_WITH_VS
    else:
        tools = [web_search, fetch_url]
        system_prompt = _SYSTEM_WEB_ONLY

    tool_map = {t.name: t for t in tools}
    llm = get_llm("retrieval").bind_tools(tools)

    plan = state["research_plan"]
    sub_questions = plan["sub_questions"] if plan else [state["query"]]

    sub_q_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(sub_questions))
    prompt_suffix = f"\n\nDirective from Supervisor: {instruction}" if instruction else ""
    context = f"Main query: {state['query']}\n\nSub-questions:\n{sub_q_text}{prompt_suffix}"

    messages = [
        SystemMessage(content=system_prompt),
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

    # Score credibility before HITL so users see real scores at approval time.
    for candidate in all_candidates:
        url = candidate.get("source_url", "")
        if not url:
            continue
        try:
            obs = await score_credibility.ainvoke({"url": url})
            if obs.startswith("SUCCESS: "):
                data = json.loads(obs[len("SUCCESS: "):])
                candidate["credibility_score"] = data["score"]
                scratchpad.append(f"[cred] {url[:60]} → {data['score']} ({data['reason']})")
        except Exception:
            pass

    # ── Loop-break signals ──

    # Increment per-sub-question attempt counters.
    retrieval_attempts = dict(state.get("retrieval_attempts", {}))
    for sq in sub_questions:
        retrieval_attempts[sq] = retrieval_attempts.get(sq, 0) + 1

    # Count chunks that are genuinely new (not seen in any prior pass).
    # Deduplicate by chunk_id (stable for vector store) and source_url (stable for web).
    prior = state.get("source_candidates", []) + state.get("approved_sources", [])
    prior_ids  = {s["chunk_id"] for s in prior}
    prior_urls = {s["source_url"] for s in prior if s.get("source_url")}
    new_chunk_count = sum(
        1 for c in all_candidates
        if c["chunk_id"] not in prior_ids
        and (not c.get("source_url") or c["source_url"] not in prior_urls)
    )
    scratchpad.append(f"[dedup] {new_chunk_count} new chunks vs {len(prior)} prior candidates")

    return {
        **state_update,
        "source_candidates": all_candidates,
        "retrieval_scratchpad": (
            (f"[supervisor directive] {instruction}\n" if instruction else "")
            + "\n".join(scratchpad)
        ),
        "retrieval_attempts": retrieval_attempts,
        "last_retrieval_new_chunk_count": new_chunk_count,
        "errors": errors_in_state,
    }
