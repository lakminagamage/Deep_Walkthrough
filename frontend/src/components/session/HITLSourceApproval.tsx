'use client'

import { useState } from 'react'
import { ExternalLink, Loader } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SourceCandidate } from '@/types/session'

interface Props {
  payload: unknown
  resumeSession: (gate: string, decision: object) => Promise<void>
}

function credColor(score: number): string {
  if (score >= 0.8) return 'text-green border-green/30 bg-green/10'
  if (score >= 0.6) return 'text-amber border-amber/30 bg-amber/10'
  return 'text-red border-red/30 bg-red/10'
}

export default function HITLSourceApproval({ payload, resumeSession }: Props) {
  const sources: SourceCandidate[] =
    (payload as { sources?: SourceCandidate[] })?.sources ?? []

  const [selected, setSelected] = useState<Set<string>>(
    new Set(sources.map(s => s.chunk_id))
  )
  const [submitting, setSubmitting] = useState(false)

  const toggle = (id: string) =>
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const toggleAll = () =>
    setSelected(selected.size === sources.length ? new Set() : new Set(sources.map(s => s.chunk_id)))

  const confirm = async () => {
    setSubmitting(true)
    try {
      await resumeSession('sources', { approved_chunk_ids: [...selected] })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 p-6 h-full overflow-hidden">
      <div className="shrink-0 border-b border-amber/30 pb-4">
        <p className="font-mono text-xs text-amber uppercase tracking-wider mb-1">Gate 2 — Source Approval</p>
        <p className="font-sans text-base text-dim">
          Select sources for the analysis phase. Deselect low-quality results.
        </p>
      </div>

      <div className="shrink-0 flex items-center justify-between">
        <span className="font-sans text-sm text-muted">
          {selected.size} of {sources.length} selected
        </span>
        <button
          onClick={toggleAll}
          className="font-mono text-sm text-blue hover:underline"
        >
          {selected.size === sources.length ? 'Deselect All' : 'Select All'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 pr-1">
        {sources.map(s => (
          <label
            key={s.chunk_id}
            className={cn(
              'flex gap-3 p-4 rounded-lg border cursor-pointer transition-colors',
              selected.has(s.chunk_id)
                ? 'border-blue/40 bg-blue/5'
                : 'border-border bg-surface hover:border-dim'
            )}
          >
            <input
              type="checkbox"
              checked={selected.has(s.chunk_id)}
              onChange={() => toggle(s.chunk_id)}
              className="mt-0.5 accent-blue shrink-0"
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-sm font-sans text-ink truncate flex-1">{s.source_title || s.source_url}</p>
                <span className={cn('text-xs font-mono px-1.5 py-0.5 rounded-md border shrink-0', credColor(s.credibility_score))}>
                  {s.credibility_score.toFixed(2)}
                </span>
              </div>
              {s.source_url && (
                <a
                  href={s.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={e => e.stopPropagation()}
                  className="flex items-center gap-1 text-xs text-blue hover:underline font-mono truncate mb-1"
                >
                  <ExternalLink size={10} />
                  {s.source_url.slice(0, 60)}
                </a>
              )}
              <p className="text-sm text-dim leading-relaxed line-clamp-2">{s.content}</p>
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={confirm}
        disabled={submitting || selected.size === 0}
        className="shrink-0 flex items-center justify-center gap-2 py-2.5 bg-blue/10 border border-blue/40
                   text-blue text-sm font-mono rounded-lg hover:bg-blue/20 transition-colors
                   disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {submitting && <Loader size={13} className="animate-spin" />}
        Confirm {selected.size} Source{selected.size !== 1 ? 's' : ''} →
      </button>
    </div>
  )
}
