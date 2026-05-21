'use client'

import Link from 'next/link'
import type { AgentState, SessionEvent } from '@/types/session'
import HITLPlanApproval from './HITLPlanApproval'
import HITLSourceApproval from './HITLSourceApproval'

interface Props {
  sessionId: string
  pendingGate: 'plan' | 'sources' | null
  hitlPayload: unknown
  latestState: AgentState | null
  events: SessionEvent[]
  complete: boolean
  reportId: string | null
  resumeSession: (gate: string, decision: object) => Promise<void>
}

export default function ActiveSurface({
  sessionId,
  pendingGate,
  hitlPayload,
  latestState,
  events,
  complete,
  resumeSession,
}: Props) {
  // ── HITL gates take priority 
  if (pendingGate === 'plan') {
    return (
      <HITLPlanApproval
        payload={hitlPayload}
        resumeSession={resumeSession}
      />
    )
  }

  if (pendingGate === 'sources') {
    return (
      <HITLSourceApproval
        payload={hitlPayload}
        resumeSession={resumeSession}
      />
    )
  }

  // ── Session complete ─────
  if (complete) {
    const score     = latestState?.critic_score ?? null
    const abandoned = score !== null && score < 0.75

    return (
      <div className="flex flex-col items-center justify-center gap-5 h-full p-8 text-center">
        <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center
                         ${abandoned ? 'border-amber' : 'border-green'}`}>
          <span className={`text-base ${abandoned ? 'text-amber' : 'text-green'}`}>
            {abandoned ? '!' : '✓'}
          </span>
        </div>

        {abandoned ? (
          <>
            <p className="font-mono text-sm text-amber uppercase tracking-wider">Research Abandoned</p>
            <p className="font-sans text-sm text-dim max-w-xs leading-relaxed">
              The system couldn't find sufficient valid information for this query.
            </p>
            {score !== null && (
              <p className="font-sans text-xs text-muted">
                Best critic score: <span className="font-mono text-red">{score.toFixed(2)}</span>
                {' '}(threshold 0.75)
              </p>
            )}
          </>
        ) : (
          <>
            <p className="font-mono text-sm text-green uppercase tracking-wider">Research Complete</p>
            {score !== null && (
              <p className="font-sans text-sm text-muted">
                Critic score: <span className="text-ink font-mono">{score.toFixed(2)}</span>
              </p>
            )}
          </>
        )}

        <Link
          href={`/report/${sessionId}`}
          className={`px-6 py-2.5 border font-mono text-sm rounded-lg transition-colors
                      ${abandoned
                        ? 'bg-amber/10 border-amber/40 text-amber hover:bg-amber/20'
                        : 'bg-green/10 border-green/40 text-green hover:bg-green/20'}`}
        >
          {abandoned ? 'View Draft →' : 'Open Report →'}
        </Link>
      </div>
    )
  }

  // ── Running: show latest agent output ─
  const lastEndEvent = [...events].reverse().find(e => e.type === 'agent_end')
  const lastToolResult = [...events].reverse().find(e => e.type === 'tool_result')

  if (!lastEndEvent && !lastToolResult && !latestState) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="font-mono text-sm text-muted animate-pulse">Initialising pipeline…</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="shrink-0 px-5 py-3 border-b border-border">
        <span className="font-mono text-xs text-muted uppercase tracking-wider">
          Latest Output
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
        {lastEndEvent && lastEndEvent.type === 'agent_end' && (
          <section>
            <p className="font-mono text-xs text-dim mb-2">
              {lastEndEvent.agent} / agent_end
            </p>
            <pre className="text-xs font-mono text-ink bg-surface rounded-lg p-4
                            overflow-auto max-h-64 whitespace-pre-wrap break-all border border-border">
              {JSON.stringify(lastEndEvent.output, null, 2)}
            </pre>
          </section>
        )}

        {/* Scratchpad snippets */}
        {latestState && (
          <>
            {latestState.supervisor_scratchpad && (
              <Scratchpad label="supervisor" text={latestState.supervisor_scratchpad} />
            )}
            {latestState.retrieval_scratchpad && (
              <Scratchpad label="retrieval" text={latestState.retrieval_scratchpad} />
            )}
            {latestState.analysis_scratchpad && (
              <Scratchpad label="analysis" text={latestState.analysis_scratchpad} />
            )}
            {latestState.synthesis_scratchpad && (
              <Scratchpad label="synthesis" text={latestState.synthesis_scratchpad} />
            )}
            {latestState.critic_scratchpad && (
              <Scratchpad label="critic" text={latestState.critic_scratchpad} />
            )}
          </>
        )}
      </div>
    </div>
  )
}

function Scratchpad({ label, text }: { label: string; text: string }) {
  return (
    <section>
      <p className="font-mono text-xs text-dim mb-2">{label} / scratchpad</p>
      <pre className="text-xs font-mono text-dim bg-surface rounded-lg p-4 border border-border
                      overflow-auto max-h-52 whitespace-pre-wrap break-words">
        {text.slice(0, 2000)}{text.length > 2000 ? '…' : ''}
      </pre>
    </section>
  )
}
