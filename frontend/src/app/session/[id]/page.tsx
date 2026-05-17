'use client'

import { useRouter } from 'next/navigation'
import { useSessionStream } from '@/hooks/useSessionStream'
import AgentProgressFeed from '@/components/session/AgentProgressFeed'
import ActiveSurface from '@/components/session/ActiveSurface'
import StateInspector from '@/components/session/StateInspector'

interface Props { params: { id: string } }

export default function SessionPage({ params }: Props) {
  const sessionId = params.id
  const stream = useSessionStream(sessionId)
  const router = useRouter()

  return (
    <div className="h-screen flex flex-col bg-base text-ink overflow-hidden">
      {/* Header */}
      <header className="shrink-0 border-b border-border px-6 py-3 flex items-center gap-4">
        <button onClick={() => router.push('/')} className="font-sans text-base font-semibold text-ink tracking-tight hover:text-dim transition-colors">DeepWalkthrough</button>
        <span className="text-border">·</span>
        <span className="font-mono text-sm text-dim">
          session <span className="text-ink">{sessionId.slice(0, 8)}</span>
        </span>
        {stream.latestState?.query && (
          <span className="font-sans text-sm text-dim truncate max-w-xl">
            {stream.latestState.query}
          </span>
        )}
        <div className="ml-auto flex items-center gap-4">
          {stream.latestState?.revision_count !== undefined && (
            <span className="font-mono text-xs text-muted">
              rev <span className="text-amber">{stream.latestState.revision_count}</span>
            </span>
          )}
          {stream.latestState?.critic_score !== null &&
           stream.latestState?.critic_score !== undefined && (
            <span className="font-mono text-xs text-muted">
              critic{' '}
              <span className={
                stream.latestState.critic_score >= 0.75 ? 'text-green' :
                stream.latestState.critic_score >= 0.5  ? 'text-amber' : 'text-red'
              }>
                {stream.latestState.critic_score.toFixed(2)}
              </span>
            </span>
          )}
          {stream.complete && (
            <button
              onClick={() => router.push(`/report/${sessionId}`)}
              className="px-4 py-1.5 bg-green/10 border border-green/40 text-green
                         text-sm font-mono rounded-lg hover:bg-green/20 transition-colors"
            >
              View Report →
            </button>
          )}
        </div>
      </header>

      {/* Three-panel body */}
      <div className="flex-1 flex divide-x divide-border overflow-hidden">
        {/* Left 30% — Agent Progress Feed */}
        <div className="w-[30%] flex flex-col overflow-hidden">
          <AgentProgressFeed events={stream.events} />
        </div>

        {/* Center 40% — Active Surface */}
        <div className="w-[40%] flex flex-col overflow-hidden">
          <ActiveSurface
            sessionId={sessionId}
            pendingGate={stream.pendingGate}
            hitlPayload={stream.hitlPayload}
            latestState={stream.latestState}
            events={stream.events}
            complete={stream.complete}
            reportId={stream.reportId}
            resumeSession={stream.resumeSession}
          />
        </div>

        {/* Right 30% — State Inspector */}
        <div className="w-[30%] flex flex-col overflow-hidden">
          <StateInspector state={stream.latestState} events={stream.events} />
        </div>
      </div>
    </div>
  )
}
