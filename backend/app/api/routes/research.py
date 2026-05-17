from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from langgraph.types import Command
from pydantic import BaseModel

from app.api.streaming import run_graph_background
from app.graph.graph import make_initial_state

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str
    document_ids: list[str] = []


class ResumeRequest(BaseModel):
    gate: str
    decision: dict


@router.post("/research")
async def start_research(
    body: ResearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    session_id = str(uuid.uuid4())
    graph = request.app.state.graph
    episodic = request.app.state.episodic
    queues: dict = request.app.state.session_queues

    await episodic.create_session(session_id, body.query)
    await episodic.log_event(session_id, "session_start", payload={"query": body.query})

    queue: asyncio.Queue = asyncio.Queue()
    queues[session_id] = queue

    config = {"configurable": {"thread_id": session_id}}
    initial_state = make_initial_state(session_id, body.query, body.document_ids)

    background_tasks.add_task(
        run_graph_background,
        graph=graph,
        initial_input=initial_state,
        config=config,
        queue=queue,
        episodic=episodic,
        session_id=session_id,
    )

    return {"session_id": session_id}


@router.post("/session/{session_id}/resume")
async def resume_session(
    session_id: str,
    body: ResumeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    queues: dict = request.app.state.session_queues
    if session_id not in queues:
        raise HTTPException(status_code=404, detail="Session not found")

    graph = request.app.state.graph
    episodic = request.app.state.episodic
    queue = queues[session_id]

    await episodic.log_hitl_decision(
        session_id,
        gate=body.gate,
        decision=body.decision.get("action", "resume"),
        payload=body.decision,
    )

    config = {"configurable": {"thread_id": session_id}}
    resume_command = Command(resume=body.decision)

    background_tasks.add_task(
        run_graph_background,
        graph=graph,
        initial_input=resume_command,
        config=config,
        queue=queue,
        episodic=episodic,
        session_id=session_id,
    )

    await episodic.update_session_status(session_id, "running")
    return {"status": "resumed"}
