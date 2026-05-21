"""SSE event formatting, LangChain callback, and background graph runner."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage

if TYPE_CHECKING:
    from app.graph.state import SupervisorDecision

AGENT_NODES = {
    "supervisor_plan",
    "hitl_plan_approval",
    "retrieval_agent",
    "hitl_source_approval",
    "analysis_agent",
    "synthesis_agent",
    "critic_agent",
    "finalize_report",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(obj: Any) -> Any:
    """Recursively coerce an object to something JSON-serialisable."""
    if isinstance(obj, dict):
        return {k: _safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def format_sse(data: dict) -> str:
    return f"data: {json.dumps(_safe(data))}\n\n"


async def emit_supervisor_decision(
    queue: asyncio.Queue,
    decision: "SupervisorDecision",
) -> None:
    await queue.put({
        "type": "supervisor_decision",
        "stage": decision["stage"],
        "next": decision["next"],
        "reasoning": decision["reasoning"],
        "instruction": decision["instruction"],
        "timestamp": decision["timestamp"],
    })


# ── LangChain callback for tool + agent events ─

class StreamEventCallback(AsyncCallbackHandler):
    """Intercepts tool calls and agent-chain starts; pushes SSE events to queue."""

    def __init__(self, queue: asyncio.Queue) -> None:
        super().__init__()
        self._queue = queue
        self._current_node = "unknown"

    async def _put(self, event: dict) -> None:
        await self._queue.put(event)

    async def on_chain_start(
        self, serialized, inputs, *, run_id, tags=None, metadata=None, **kwargs
    ) -> None:
        node = (metadata or {}).get("langgraph_node", "")
        if node in AGENT_NODES:
            self._current_node = node
            await self._put({
                "type": "agent_start",
                "agent": node,
                "node": node,
                "timestamp": _now(),
            })

    async def on_tool_start(
        self, serialized, input_str, *, run_id, tags=None, metadata=None, **kwargs
    ) -> None:
        tool_name = serialized.get("name", "unknown")
        agent = (metadata or {}).get("langgraph_node", self._current_node)
        await self._put({
            "type": "tool_call",
            "agent": agent,
            "tool": tool_name,
            "input": input_str if isinstance(input_str, dict) else {"input": input_str},
            "timestamp": _now(),
        })

    async def on_tool_end(
        self, output, *, run_id, tags=None, metadata=None, **kwargs
    ) -> None:
        tool_name = kwargs.get("name", "unknown")
        agent = (metadata or {}).get("langgraph_node", self._current_node)
        await self._put({
            "type": "tool_result",
            "agent": agent,
            "tool": tool_name,
            "result": {"output": str(output)[:600]},
            "timestamp": _now(),
        })


# ── Background graph runner ─

async def _generate_summary(query: str) -> str:
    """Return a ≤10-word summary of the query using the LLM."""
    try:
        from app.config import get_llm
        llm = get_llm("supervisor")
        resp = await llm.ainvoke([
            SystemMessage(content=(
                "Summarise the research question in 10 words or fewer. "
                "Be specific and descriptive. Output only the summary, no punctuation."
            )),
            HumanMessage(content=query),
        ])
        return str(resp.content).strip()
    except Exception:
        return query[:80]


async def run_graph_background(
    *,
    graph,
    initial_input,
    config: dict,
    queue: asyncio.Queue,
    episodic,
    session_id: str,
) -> None:
    """
    Streams a LangGraph run into `queue` as SSE-ready dicts.

    Sends None to queue as the SSE close sentinel on terminal exit.
    On HITL interrupt, returns WITHOUT sending None so the SSE connection
    stays alive and post-approval events flow through the same stream.
    """
    # Generate and persist a human-readable summary for new sessions only.
    from langgraph.types import Command as LGCommand
    if not isinstance(initial_input, LGCommand):
        query = (initial_input or {}).get("query", "")
        if query:
            summary = await _generate_summary(query)
            await episodic.update_session_summary(session_id, summary)

    callback = StreamEventCallback(queue)
    run_config = {
        **config,
        "callbacks": [callback],
    }
    _hitl_pause = False

    try:
        async for chunk in graph.astream(
            initial_input, run_config, stream_mode="updates"
        ):
            for node_name, node_output in chunk.items():

                if node_name == "__interrupt__":
                    for intr in node_output:
                        payload = intr.value if hasattr(intr, "value") else intr
                        gate = (
                            payload.get("gate")
                            if isinstance(payload, dict)
                            else "unknown"
                        )
                        await queue.put({
                            "type": "hitl_interrupt",
                            "gate": gate,
                            "payload": _safe(payload),
                            "timestamp": _now(),
                        })
                    await episodic.update_session_status(session_id, "hitl_wait")
                    _hitl_pause = True
                    return  # finally checks _hitl_pause and skips the None sentinel

                if node_name == "supervisor_route":
                    decisions = node_output.get("supervisor_decisions", [])
                    if decisions:
                        await emit_supervisor_decision(queue, decisions[-1])

                elif node_name in AGENT_NODES:
                    await queue.put({
                        "type": "agent_end",
                        "agent": node_name,
                        "node": node_name,
                        "output": _safe(node_output),
                        "timestamp": _now(),
                    })

                # State snapshot after every node.
                state = await graph.aget_state(config)
                await queue.put({
                    "type": "state_snapshot",
                    "state": _safe(dict(state.values)),
                    "timestamp": _now(),
                })

        # ── Normal completion ────
        final_state = await graph.aget_state(config)
        report_id = (final_state.values or {}).get("report_id")
        if (final_state.values or {}).get("report_final"):
            await queue.put({
                "type": "session_complete",
                "report_id": report_id,
                "timestamp": _now(),
            })
            await episodic.update_session_status(session_id, "complete", report_id)
        else:
            await episodic.update_session_status(session_id, "complete")

    except Exception as exc:
        await queue.put({
            "type": "error",
            "message": str(exc),
            "recoverable": False,
            "timestamp": _now(),
        })
        await episodic.update_session_status(session_id, "error")

    finally:
        if not _hitl_pause:
            await queue.put(None)  # SSE close sentinel — skipped on HITL to keep stream open
