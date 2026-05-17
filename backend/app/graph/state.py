from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ResearchPlan(TypedDict):
    sub_questions: list[str]
    approved: bool


class SourceCandidate(TypedDict):
    chunk_id: str
    content: str
    source_url: str
    source_title: str
    page_number: int | None
    credibility_score: float
    approved: bool


class Claim(TypedDict):
    text: str
    chunk_ids: list[str]   # citations — chunk IDs from SourceCandidate
    confidence: float


class AgentState(TypedDict):
    # Core inputs
    session_id: str
    query: str
    document_ids: list[str]        # pre-ingested doc IDs to include in retrieval

    # Planning
    research_plan: ResearchPlan | None
    hitl_plan_approved: bool

    # Retrieval
    source_candidates: list[SourceCandidate]
    approved_sources: list[SourceCandidate]
    hitl_sources_approved: bool

    # Analysis
    claims: list[Claim]
    analysis_gaps: list[str]       # topics not covered by retrieved sources

    # Synthesis
    report_draft: str | None
    report_final: str | None
    report_id: str | None

    # Critic
    critic_score: float | None
    critic_feedback: str | None
    revision_count: int

    # Reasoning scratchpads — always populated, never discarded
    supervisor_scratchpad: str
    retrieval_scratchpad: str
    analysis_scratchpad: str
    synthesis_scratchpad: str
    critic_scratchpad: str

    # Message history (LangGraph managed)
    messages: Annotated[list, add_messages]

    # Errors encountered during the run
    errors: list[dict]             # [{agent, tool, error_message, timestamp}]
