'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { RefreshCw } from 'lucide-react'
import { API_BASE, cn } from '@/lib/utils'

interface Session {
  id: string
  query: string
  status: 'running' | 'hitl_wait' | 'complete' | 'error'
  created_at: string
  completed_at: string | null
  report_id: string | null
}

const STATUS_STYLE: Record<Session['status'], string> = {
  complete:  'text-green  bg-green/10  border-green/30',
  running:   'text-blue   bg-blue/10   border-blue/30',
  hitl_wait: 'text-amber  bg-amber/10  border-amber/30',
  error:     'text-red    bg-red/10    border-red/30',
}

const STATUS_LABEL: Record<Session['status'], string> = {
  complete:  'complete',
  running:   'running',
  hitl_wait: 'awaiting input',
  error:     'error',
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60)   return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60)   return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24)   return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function SessionHistory() {
  const router = useRouter()
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading]   = useState(true)
  const [spinning, setSpinning] = useState(false)

  const load = async (showSpinner = false) => {
    if (showSpinner) setSpinning(true)
    try {
      const res = await fetch(`${API_BASE}/api/sessions`)
      if (!res.ok) return
      const data = await res.json()
      setSessions(data.sessions ?? [])
    } catch {
      // backend not reachable — silently ignore
    } finally {
      setLoading(false)
      if (showSpinner) setSpinning(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  // Auto-refresh while any session is still active.
  useEffect(() => {
    const hasActive = sessions.some(s => s.status === 'running' || s.status === 'hitl_wait')
    if (!hasActive) return
    const timer = setInterval(() => load(), 5000)
    return () => clearInterval(timer)
  }, [sessions])

  if (loading) return null

  if (sessions.length === 0) {
    return (
      <section className="border-t border-border px-10 py-8">
        <p className="font-mono text-xs text-muted uppercase tracking-wider mb-1">Session History</p>
        <p className="font-sans text-sm text-muted mt-3">No sessions yet.</p>
      </section>
    )
  }

  return (
    <section className="border-t border-border px-10 py-8">
      <div className="flex items-center justify-between mb-5">
        <p className="font-mono text-xs text-muted uppercase tracking-wider">Session History</p>
        <button
          onClick={() => load(true)}
          className="flex items-center gap-1.5 font-mono text-xs text-dim hover:text-ink transition-colors"
        >
          <RefreshCw size={12} className={cn(spinning && 'animate-spin')} />
          Refresh
        </button>
      </div>

      <div className="flex flex-col divide-y divide-border rounded-lg border border-border overflow-hidden">
        {sessions.map(s => (
          <button
            key={s.id}
            onClick={() => router.push(`/session/${s.id}`)}
            className="flex items-center gap-4 px-5 py-4 text-left hover:bg-raised/60 transition-colors group"
          >
            {/* ID */}
            <span className="font-mono text-xs text-muted shrink-0 w-20">
              {s.id.slice(0, 8)}
            </span>

            {/* Query */}
            <span className="font-sans text-sm text-ink flex-1 truncate group-hover:text-ink/90">
              {s.query}
            </span>

            {/* Status badge */}
            <span className={cn(
              'font-mono text-xs px-2 py-0.5 rounded-md border shrink-0',
              STATUS_STYLE[s.status]
            )}>
              {STATUS_LABEL[s.status]}
            </span>

            {/* Time */}
            <span className="font-mono text-xs text-muted shrink-0 w-20 text-right">
              {timeAgo(s.created_at)}
            </span>

            {/* Report shortcut */}
            {s.status === 'complete' && s.report_id && (
              <button
                onClick={e => { e.stopPropagation(); router.push(`/session/${s.id}`) }}
                className="font-mono text-xs text-blue hover:underline shrink-0"
              >
                report →
              </button>
            )}
          </button>
        ))}
      </div>
    </section>
  )
}
