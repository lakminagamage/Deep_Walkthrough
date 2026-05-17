from __future__ import annotations

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph

from app.agents.analysis import analysis_node
from app.agents.critic import critic_node
from app.agents.retrieval import retrieval_node
from app.agents.supervisor import supervisor_node
from app.agents.synthesis import synthesis_node
from app.graph.hitl import (
    hitl_plan_approval_node,
    hitl_source_approval_node,
    route_after_critic,
)
from app.graph.state import AgentState


def build_graph(checkpointer: AsyncSqliteSaver):
    g = StateGraph(AgentState)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    g.add_node("supervisor",            supervisor_node)
    g.add_node("hitl_plan_approval",    hitl_plan_approval_node)
    g.add_node("retrieval_agent",       retrieval_node)
    g.add_node("hitl_source_approval",  hitl_source_approval_node)
    g.add_node("analysis_agent",        analysis_node)
    g.add_node("synthesis_agent",       synthesis_node)
    g.add_node("critic_agent",          critic_node)

    # ── Static edges (nodes that return plain dicts) ──────────────────────────
    g.set_entry_point("supervisor")
    g.add_edge("supervisor",        "hitl_plan_approval")
    # hitl_plan_approval  → retrieval_agent | END  (via Command inside the node)
    g.add_edge("retrieval_agent",   "hitl_source_approval")
    # hitl_source_approval → analysis_agent        (via Command inside the node)
    g.add_edge("analysis_agent",    "synthesis_agent")
    g.add_edge("synthesis_agent",   "critic_agent")

    # ── Conditional edge: critic loop ─────────────────────────────────────────
    g.add_conditional_edges(
        "critic_agent",
        route_after_critic,
        {"synthesis_agent": "synthesis_agent", END: END},
    )

    return g.compile(checkpointer=checkpointer)


def make_initial_state(session_id: str, query: str) -> AgentState:
    return {
        "session_id":           session_id,
        "query":                query,
        "document_ids":         [],
        "research_plan":        None,
        "hitl_plan_approved":   False,
        "source_candidates":    [],
        "approved_sources":     [],
        "hitl_sources_approved": False,
        "claims":               [],
        "analysis_gaps":        [],
        "report_draft":         None,
        "report_final":         None,
        "report_id":            None,
        "critic_score":         None,
        "critic_feedback":      None,
        "revision_count":       0,
        "supervisor_scratchpad":  "",
        "retrieval_scratchpad":   "",
        "analysis_scratchpad":    "",
        "synthesis_scratchpad":   "",
        "critic_scratchpad":      "",
        "messages":             [],
        "errors":               [],
    }
