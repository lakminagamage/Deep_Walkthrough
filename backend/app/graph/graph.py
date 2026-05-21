from __future__ import annotations

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph

from app.agents.analysis import analysis_node
from app.agents.critic import critic_node
from app.agents.finalize import finalize_report_node
from app.agents.retrieval import retrieval_node
from app.agents.supervisor import supervisor_plan_node, supervisor_route_node
from app.agents.synthesis import synthesis_node
from app.graph.hitl import (
    hitl_plan_approval_node,
    hitl_source_approval_node,
)
from app.graph.state import AgentState


def _route_from_supervisor(state: AgentState) -> str:
    decisions = state.get("supervisor_decisions", [])
    if not decisions:
        return "analysis_agent"
    latest = decisions[-1]
    mapping = {
        "analysis":   "analysis_agent",
        "retrieval":  "retrieval_agent",
        "synthesis":  "synthesis_agent",
        "end":        "finalize_report",
    }
    return mapping.get(latest.get("next"), "analysis_agent")


def build_graph(checkpointer: AsyncSqliteSaver):
    g = StateGraph(AgentState)

    # ── Nodes 
    g.add_node("supervisor_plan",       supervisor_plan_node)
    g.add_node("supervisor_route",      supervisor_route_node)
    g.add_node("hitl_plan_approval",    hitl_plan_approval_node)
    g.add_node("retrieval_agent",       retrieval_node)
    g.add_node("hitl_source_approval",  hitl_source_approval_node)
    g.add_node("analysis_agent",        analysis_node)
    g.add_node("synthesis_agent",       synthesis_node)
    g.add_node("critic_agent",          critic_node)
    g.add_node("finalize_report",       finalize_report_node)

    # ── Edges 
    g.set_entry_point("supervisor_plan")
    g.add_edge("supervisor_plan",   "hitl_plan_approval")
    # hitl_plan_approval → retrieval_agent | END  (via Command inside the node)

    g.add_edge("retrieval_agent",   "hitl_source_approval")
    # hitl_source_approval → supervisor_route     (via Command inside the node)

    # ── Conditional edge from supervisor_route ─
    g.add_conditional_edges(
        "supervisor_route",
        _route_from_supervisor,
        {
            "analysis_agent":  "analysis_agent",
            "retrieval_agent": "retrieval_agent",
            "synthesis_agent": "synthesis_agent",
            "finalize_report": "finalize_report",
        },
    )

    g.add_edge("analysis_agent",  "supervisor_route")
    g.add_edge("critic_agent",    "supervisor_route")
    g.add_edge("synthesis_agent", "critic_agent")
    g.add_edge("finalize_report", END)

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
        "best_report_draft":    None,
        "report_final":         None,
        "report_id":            None,
        "critic_score":         None,
        "best_critic_score":    None,
        "critic_feedback":      None,
        "revision_count":       0,
        "supervisor_scratchpad":  "",
        "retrieval_scratchpad":   "",
        "analysis_scratchpad":    "",
        "synthesis_scratchpad":   "",
        "critic_scratchpad":      "",
        "messages":             [],
        "errors":               [],
        "supervisor_decisions": [],
        "current_supervisor_instruction": None,
        "retrieval_attempts":   {},
        "last_retrieval_new_chunk_count": -1,
    }
