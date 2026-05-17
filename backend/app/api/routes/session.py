from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()

_HEARTBEAT_INTERVAL = 25  # seconds


@router.get("/session/{session_id}/stream")
async def stream_session(session_id: str, request: Request) -> StreamingResponse:
    queues: dict = request.app.state.session_queues
    if session_id not in queues:
        raise HTTPException(status_code=404, detail="Session not found")

    queue: asyncio.Queue = queues[session_id]

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    yield 'data: {"type":"heartbeat"}\n\n'
                    continue

                if event is None:
                    # Terminal sentinel — session is complete or errored.
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
