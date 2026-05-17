from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.streaming import _now, _safe, format_sse

router = APIRouter()

_HEARTBEAT_INTERVAL = 25  # seconds


@router.get("/sessions")
async def list_sessions(request: Request) -> dict:
    episodic = request.app.state.episodic
    sessions = await episodic.list_sessions(limit=30)
    return {"sessions": sessions}


@router.get("/session/{session_id}/stream")
async def stream_session(session_id: str, request: Request) -> StreamingResponse:
    episodic = request.app.state.episodic
    graph    = request.app.state.graph
    queues: dict = request.app.state.session_queues

    session = await episodic.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Ensure a queue exists even after a server restart.
    if session_id not in queues:
        queues[session_id] = asyncio.Queue()
    queue = queues[session_id]

    config = {"configurable": {"thread_id": session_id}}
    status = session["status"]

    async def generate():
        try:
            # ── Replay current graph state on every (re)connect ───────────
            graph_state = await graph.aget_state(config)
            vals = graph_state.values if graph_state else {}

            if vals:
                yield format_sse({
                    "type": "state_snapshot",
                    "state": _safe(dict(vals)),
                    "timestamp": _now(),
                })

            if status == "complete":
                yield format_sse({
                    "type": "session_complete",
                    "report_id": session.get("report_id"),
                    "timestamp": _now(),
                })
                yield 'data: {"type":"done"}\n\n'
                return

            if status == "error":
                yield format_sse({
                    "type": "error",
                    "message": "Session ended with an error.",
                    "recoverable": False,
                    "timestamp": _now(),
                })
                yield 'data: {"type":"done"}\n\n'
                return

            if status == "hitl_wait":
                # Re-emit the pending HITL interrupt from the graph checkpoint.
                for task in (graph_state.tasks if graph_state else []):
                    if hasattr(task, "interrupts") and task.interrupts:
                        for intr in task.interrupts:
                            payload = intr.value if hasattr(intr, "value") else intr
                            gate = (
                                payload.get("gate")
                                if isinstance(payload, dict)
                                else "unknown"
                            )
                            yield format_sse({
                                "type": "hitl_interrupt",
                                "gate": gate,
                                "payload": _safe(payload),
                                "timestamp": _now(),
                            })

            # ── Stream live events from the queue ─────────────────────────
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    yield 'data: {"type":"heartbeat"}\n\n'
                    continue

                if event is None:
                    yield 'data: {"type":"done"}\n\n'
                    break

                yield f"data: {json.dumps(event)}\n\n"

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
