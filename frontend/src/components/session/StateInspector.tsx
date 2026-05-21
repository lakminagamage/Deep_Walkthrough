'use client'

import { useMemo, useRef, useState } from 'react'
import type { AgentState, SessionEvent, SupervisorDecision } from '@/types/session'
import dynamic from 'next/dynamic'

const ReactJson = dynamic(() => import('@microlink/react-json-view'), { ssr: false })

const stageLabel: Record<string, string> = {
  post_sources:  "After source approval",
  post_analysis: "After analysis",
  post_critic:   "After critic review",
}

const nextBadge: Record<string, string> = {
  analysis:  "bg-teal-500/15 text-teal-400",
  synthesis: "bg-teal-500/15 text-teal-400",
  retrieval: "bg-amber-500/15 text-amber-400",
  end:       "bg-zinc-500/15 text-zinc-400",
}

function SupervisorDecisionRow({ d, index }: { d: SupervisorDecision; index: number }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-purple-500/20 rounded-md overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-purple-500/5 transition-colors"
      >
        <span className="font-mono text-xs text-muted">#{index + 1}</span>
        <span className="font-mono text-xs text-purple-300">{stageLabel[d.stage] ?? d.stage}</span>
        <span className={`font-mono text-xs px-1.5 py-0.5 rounded ${nextBadge[d.next] ?? nextBadge.end}`}>
          → {d.next}
        </span>
        <span className="ml-auto font-mono text-xs text-muted">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-purple-500/10">
          <div className="mt-2">
            <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">Reasoning</div>
            <pre className="font-mono text-xs text-ink/80 bg-raised/50 rounded p-2 whitespace-pre-wrap leading-relaxed overflow-auto max-h-32">
              {d.reasoning}
            </pre>
          </div>
          <div>
            <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">Instruction</div>
            {d.instruction ? (
              <div className="font-mono text-xs text-amber-200 bg-amber-500/10 rounded p-2 whitespace-pre-wrap">
                {d.instruction}
              </div>
            ) : (
              <span className="font-mono text-xs text-muted italic">None</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface Props {
  state: AgentState | null
  events: SessionEvent[]
}

export default function StateInspector({ state, events }: Props) {
  const [filter, setFilter] = useState('')
  const [copied, setCopied] = useState(false)
  const prevRef = useRef<AgentState | null>(null)

  const copyToClipboard = () => {
    if (!state) return
    navigator.clipboard.writeText(JSON.stringify(state, null, 2)).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const changedKeys = useMemo<Set<string>>(() => {
    if (!state || !prevRef.current) return new Set()
    const prev = prevRef.current
    return new Set(
      (Object.keys(state) as (keyof AgentState)[]).filter(
        k => JSON.stringify(state[k]) !== JSON.stringify(prev[k])
      )
    )
  }, [state])

  const prevSnaps = events.filter(e => e.type === 'state_snapshot')
  const prevSnap = prevSnaps.length >= 2
    ? (prevSnaps[prevSnaps.length - 2] as { type: 'state_snapshot'; state: AgentState })
    : null
  if (prevSnap) prevRef.current = prevSnap.state

  if (!state) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="font-mono text-sm text-muted">No state yet</p>
      </div>
    )
  }

  const filteredState = filter
    ? Object.fromEntries(
        Object.entries(state).filter(([k]) =>
          k.toLowerCase().includes(filter.toLowerCase())
        )
      )
    : state

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="shrink-0 px-5 py-3 border-b border-border flex items-center gap-2">
        <span className="font-mono text-xs text-muted uppercase tracking-wider">
          State
        </span>
        <input
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="filter keys…"
          className="ml-auto bg-raised border border-border rounded-lg px-3 py-1
                     text-xs font-mono text-ink placeholder-muted
                     focus:outline-none focus:border-blue w-36"
        />
        <button
          onClick={copyToClipboard}
          title="Copy full state JSON to clipboard"
          className="shrink-0 font-mono text-xs px-2 py-1 rounded-md border border-border
                     text-muted hover:text-ink hover:border-dim transition-colors"
        >
          {copied ? 'copied ✓' : 'copy'}
        </button>
      </div>

      {changedKeys.size > 0 && (
        <div className="shrink-0 px-5 py-2 bg-amber/5 border-b border-amber/20 flex flex-wrap gap-1.5">
          {[...changedKeys].map(k => (
            <span key={k} className="font-mono text-xs text-amber bg-amber/10 px-2 py-0.5 rounded-md">
              {k}
            </span>
          ))}
        </div>
      )}

      {/* Supervisor decisions section */}
      {state.supervisor_decisions && state.supervisor_decisions.length > 0 && (
        <div className="shrink-0 px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-mono text-xs text-purple-300 uppercase tracking-wider">
              Supervisor Decisions
            </span>
            <span className="font-mono text-xs bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full">
              {state.supervisor_decisions.length}
            </span>
          </div>
          <div className="space-y-1.5">
            {state.supervisor_decisions.map((d, i) => (
              <SupervisorDecisionRow key={d.timestamp} d={d} index={i} />
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        <ReactJson
          src={filteredState as object}
          theme="monokai"
          collapsed={1}
          enableClipboard={false}
          displayDataTypes={false}
          displayObjectSize={false}
          style={{ fontSize: '13px', background: 'transparent', fontFamily: 'var(--font-mono)' }}
          iconStyle="triangle"
        />
      </div>
    </div>
  )
}
