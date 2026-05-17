'use client'

import { useEffect, useRef } from 'react'
import type { SessionEvent } from '@/types/session'
import GraphStepCard from './GraphStepCard'

interface Props { events: SessionEvent[] }

export default function AgentProgressFeed({ events }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  const visible = events.filter(
    e => e.type !== 'heartbeat' && e.type !== 'done' && e.type !== 'state_snapshot'
  )

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="shrink-0 px-5 py-3 border-b border-border">
        <span className="font-mono text-xs text-muted uppercase tracking-wider">
          Agent Timeline
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-0.5">
        {visible.length === 0 ? (
          <p className="font-mono text-sm text-muted mt-6 px-2">Waiting for pipeline to start…</p>
        ) : (
          visible.map((event, i) => (
            <GraphStepCard key={i} event={event} index={i} />
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
