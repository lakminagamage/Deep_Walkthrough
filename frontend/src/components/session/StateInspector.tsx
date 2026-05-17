'use client'

import { useMemo, useRef, useState } from 'react'
import type { AgentState, SessionEvent } from '@/types/session'
import dynamic from 'next/dynamic'

const ReactJson = dynamic(() => import('@microlink/react-json-view'), { ssr: false })

interface Props {
  state: AgentState | null
  events: SessionEvent[]
}

export default function StateInspector({ state, events }: Props) {
  const [filter, setFilter] = useState('')
  const prevRef = useRef<AgentState | null>(null)

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
