'use client'

import { useState } from 'react'

interface SupervisorDecisionEvent {
  type: "supervisor_decision"
  stage: "post_sources" | "post_analysis" | "post_critic"
  next: "analysis" | "retrieval" | "synthesis" | "end"
  reasoning: string
  instruction: string | null
  timestamp: string
}

interface Props {
  event: SupervisorDecisionEvent
}

const stageLabel: Record<string, string> = {
  post_sources:  "After source approval",
  post_analysis: "After analysis",
  post_critic:   "After critic review",
}

const nextLabel: Record<string, string> = {
  analysis:  "Analysis agent",
  retrieval: "Retrieval agent — loop back",
  synthesis: "Synthesis agent",
  end:       "Pipeline complete",
}

const badgeClass: Record<string, string> = {
  analysis:  "bg-teal-500/15 text-teal-400 border border-teal-500/30",
  synthesis: "bg-teal-500/15 text-teal-400 border border-teal-500/30",
  retrieval: "bg-amber-500/15 text-amber-400 border border-amber-500/30",
  end:       "bg-zinc-500/15 text-zinc-400 border border-zinc-500/30",
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ts
  }
}

export default function SupervisorDecisionCard({ event }: Props) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="w-full my-2 rounded-lg overflow-hidden border border-purple-500/20 bg-purple-950/10">
      {/* Purple left bar + header row */}
      <div className="flex">
        <div className="w-1 shrink-0 bg-purple-500" />
        <div className="flex-1 px-4 py-3">
          {/* Header row */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Stage label */}
            <span className="font-mono text-xs text-purple-300 uppercase tracking-wider shrink-0">
              {stageLabel[event.stage] ?? event.stage}
            </span>

            {/* Routing arrow */}
            <div className="flex items-center gap-1.5 flex-1">
              <span className="font-mono text-xs text-muted">→</span>
              <span
                className={`font-mono text-xs px-2 py-0.5 rounded-full ${badgeClass[event.next] ?? badgeClass.end}`}
              >
                {nextLabel[event.next] ?? event.next}
              </span>
            </div>

            {/* Timestamp + toggle */}
            <div className="flex items-center gap-3 ml-auto shrink-0">
              <span className="font-mono text-xs text-muted">{formatTimestamp(event.timestamp)}</span>
              <button
                onClick={() => setExpanded(v => !v)}
                className="font-mono text-xs text-purple-400 hover:text-purple-200 transition-colors"
              >
                {expanded ? '▲ hide' : '▼ details'}
              </button>
            </div>
          </div>

          {/* Expandable section */}
          {expanded && (
            <div className="mt-3 space-y-3 border-t border-purple-500/10 pt-3">
              {/* Reasoning */}
              <div>
                <div className="font-mono text-xs text-purple-300 uppercase tracking-wider mb-1">
                  Reasoning
                </div>
                <pre className="font-mono text-xs text-ink/80 bg-raised/50 rounded-md p-3 whitespace-pre-wrap leading-relaxed overflow-auto max-h-48">
                  {event.reasoning}
                </pre>
              </div>

              {/* Instruction */}
              <div>
                <div className="font-mono text-xs text-purple-300 uppercase tracking-wider mb-1">
                  Instruction to next agent
                </div>
                {event.instruction ? (
                  <div className="font-mono text-xs text-amber-200 bg-amber-500/10 border border-amber-500/20 rounded-md p-3 whitespace-pre-wrap leading-relaxed">
                    {event.instruction}
                  </div>
                ) : (
                  <div className="font-mono text-xs text-muted italic">
                    No directive — proceeding with current state.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
