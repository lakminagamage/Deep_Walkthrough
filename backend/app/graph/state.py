from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages


class ResearchPlan(TypedDict):
    sub_questions: list[str]
    approved: bool


class SupervisorDecision(TypedDict):
    stage: Literal["post_sources", "post_analysis", "post_critic"]
    next: Literal["analysis", "retrieval", "synthesis", "end"]
    reasoning: str          # full CoT reasoning — stored in state, never discarded
    instruction: str | None # directive passed to the next agent; None if routing to end
    timestamp: str          # ISO format


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
    best_report_draft: str | None   # highest-scoring draft seen so far
    report_final: str | None
    report_id: str | None

    # Critic
    critic_score: float | None
    best_critic_score: float | None  # score of best_report_draft
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

    # Supervisor routing history — append-only, never overwrite
    supervisor_decisions: list[SupervisorDecision]

    # The most recent instruction from the Supervisor for the next agent to read.
    # Each agent reads this at the start of its node and incorporates it into its prompt.
    # Reset to None after each agent reads it.
    current_supervisor_instruction: str | None

    # Loop-break signals for the Supervisor
    retrieval_attempts: dict[str, int]  # sub_question → cumulative attempt count
    last_retrieval_new_chunk_count: int # chunks not seen in any prior pass; -1 = not yet run
