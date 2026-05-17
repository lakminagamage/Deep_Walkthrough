export interface ResearchPlan {
  sub_questions: string[]
  approved: boolean
}

export interface SourceCandidate {
  chunk_id: string
  content: string
  source_url: string
  source_title: string
  page_number: number | null
  credibility_score: number
  approved: boolean
}

export interface Claim {
  text: string
  chunk_ids: string[]
  confidence: number
}

export interface ErrorEntry {
  agent: string
  tool: string
  error_message: string
  timestamp: string
}

export interface AgentState {
  session_id: string
  query: string
  document_ids: string[]
  research_plan: ResearchPlan | null
  hitl_plan_approved: boolean
  source_candidates: SourceCandidate[]
  approved_sources: SourceCandidate[]
  hitl_sources_approved: boolean
  claims: Claim[]
  analysis_gaps: string[]
  report_draft: string | null
  report_final: string | null
  report_id: string | null
  critic_score: number | null
  critic_feedback: string | null
  revision_count: number
  supervisor_scratchpad: string
  retrieval_scratchpad: string
  analysis_scratchpad: string
  synthesis_scratchpad: string
  critic_scratchpad: string
  messages: unknown[]
  errors: ErrorEntry[]
}

export type SessionEvent =
  | { type: 'agent_start';      agent: string; node: string; timestamp: string }
  | { type: 'agent_end';        agent: string; node: string; output: unknown; timestamp: string }
  | { type: 'tool_call';        agent: string; tool: string; input: unknown; timestamp: string }
  | { type: 'tool_result';      agent: string; tool: string; result: unknown; timestamp: string }
  | { type: 'state_snapshot';   state: AgentState; timestamp: string }
  | { type: 'hitl_interrupt';   gate: 'plan' | 'sources'; payload: unknown; timestamp: string }
  | { type: 'session_complete'; report_id: string; timestamp: string }
  | { type: 'error';            message: string; recoverable: boolean; timestamp: string }
  | { type: 'heartbeat' }
  | { type: 'done' }

export interface StreamState {
  events: SessionEvent[]
  latestState: AgentState | null
  pendingGate: 'plan' | 'sources' | null
  hitlPayload: unknown
  reportId: string | null
  complete: boolean
  error: string | null
}
