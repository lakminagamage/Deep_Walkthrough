'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SessionEvent } from '@/types/session'

const AGENT_COLORS: Record<string, string> = {
  supervisor:           'border-purple',
  hitl_plan_approval:   'border-amber',
  retrieval_agent:      'border-blue',
  hitl_source_approval: 'border-amber',
  analysis_agent:       'border-green',
  synthesis_agent:      'border-ink',
  critic_agent:         'border-red',
}

const STATUS_DOT: Record<string, string> = {
  agent_start:    'bg-blue animate-pulse-fast',
  agent_end:      'bg-green',
  tool_call:      'bg-amber animate-pulse-fast',
  tool_result:    'bg-amber/60',
  hitl_interrupt: 'bg-amber',
  error:          'bg-red',
}

interface Props { event: SessionEvent; index: number }

export default function GraphStepCard({ event }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (event.type === 'heartbeat' || event.type === 'done' || event.type === 'state_snapshot')
    return null

  const agent = 'agent' in event ? event.agent : event.type === 'hitl_interrupt' ? 'hitl' : ''
  const borderColor = AGENT_COLORS[agent] ?? 'border-border'
  const dotColor = STATUS_DOT[event.type] ?? 'bg-muted'

  const label =
    event.type === 'agent_start'     ? `${event.agent} ▶` :
    event.type === 'agent_end'       ? `${event.agent} ✓` :
    event.type === 'tool_call'       ? `→ ${event.tool}` :
    event.type === 'tool_result'     ? `← ${event.tool}` :
    event.type === 'hitl_interrupt'  ? `⏸  HITL: ${event.gate}` :
    event.type === 'session_complete'? '✓ complete' :
    event.type === 'error'           ? `⚠ error` :
    event.type

  const ts = 'timestamp' in event
    ? new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : ''

  const hasPayload = event.type === 'agent_end'     ||
                     event.type === 'tool_call'      ||
                     event.type === 'tool_result'    ||
                     event.type === 'hitl_interrupt' ||
                     event.type === 'error'

  return (
    <div
      className={cn(
        'border-l-2 pl-3 py-2.5 cursor-pointer select-none hover:bg-raised/50 rounded-r transition-colors',
        borderColor
      )}
      onClick={() => hasPayload && setExpanded(v => !v)}
    >
      <div className="flex items-center gap-2">
        <span className={cn('w-2 h-2 rounded-full shrink-0', dotColor)} />
        <span className="font-mono text-sm text-ink flex-1 truncate">{label}</span>
        <span className="font-mono text-xs text-muted shrink-0">{ts}</span>
        {hasPayload && (
          expanded
            ? <ChevronDown size={12} className="text-muted shrink-0" />
            : <ChevronRight size={12} className="text-muted shrink-0" />
        )}
      </div>

      {expanded && hasPayload && (
        <pre className="mt-2 text-xs font-mono text-dim bg-surface rounded-lg p-3 overflow-auto max-h-52 whitespace-pre-wrap break-all">
          {JSON.stringify(
            event.type === 'agent_end'      ? event.output :
            event.type === 'tool_call'      ? event.input :
            event.type === 'tool_result'    ? event.result :
            event.type === 'hitl_interrupt' ? event.payload :
            event.type === 'error'          ? event.message :
            null,
            null, 2
          )}
        </pre>
      )}
    </div>
  )
}
