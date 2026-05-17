'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Copy, Download } from 'lucide-react'
import { API_BASE } from '@/lib/utils'
import ReportViewer from '@/components/report/ReportViewer'
import type { CitationMeta } from '@/components/report/CitationTooltip'

interface ReportData {
  report_id: string
  session_id: string
  query: string
  report_final: string
  citations: Record<string, CitationMeta>
  critic_score: number | null
  revision_count: number
}

interface Props { params: { id: string } }

export default function ReportPage({ params }: Props) {
  const sessionId = params.id
  const router = useRouter()
  const [data, setData]       = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied]   = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/api/report/${sessionId}`)
      .then(r => r.ok ? r.json() : null)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [sessionId])

  const copyMarkdown = async () => {
    if (!data) return
    await navigator.clipboard.writeText(data.report_final)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadMarkdown = () => {
    if (!data) return
    const blob = new Blob([data.report_final], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `report-${data.report_id.slice(0, 8)}.md`
    a.click()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="font-mono text-sm text-muted animate-pulse">Loading report…</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <p className="font-sans text-base text-red">Report not found</p>
        <button onClick={() => router.back()} className="font-mono text-sm text-blue hover:underline">
          ← Back
        </button>
      </div>
    )
  }

  const citationEntries = Object.entries(data.citations ?? {})

  return (
    <div className="min-h-screen bg-base flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-base/95 backdrop-blur px-8 py-4
                         flex items-center gap-4">
        <button onClick={() => router.push('/')} className="font-sans text-base font-semibold text-ink tracking-tight hover:text-dim transition-colors">DeepWalkthrough</button>
        <span className="text-border">·</span>
        <button onClick={() => router.back()} className="font-mono text-sm text-dim hover:text-ink">
          ← session
        </button>
        <span className="font-sans text-sm text-muted flex-1 truncate">{data.query}</span>

        <div className="flex items-center gap-3 shrink-0">
          {data.critic_score !== null && (
            <span className="font-mono text-xs text-muted">
              critic{' '}
              <span className={
                (data.critic_score ?? 0) >= 0.75 ? 'text-green' :
                (data.critic_score ?? 0) >= 0.5  ? 'text-amber' : 'text-red'
              }>
                {data.critic_score?.toFixed(2)}
              </span>
            </span>
          )}
          <button
            onClick={copyMarkdown}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-border rounded-lg
                       font-mono text-sm text-dim hover:text-ink hover:border-dim transition-colors"
          >
            <Copy size={13} />
            {copied ? 'Copied!' : 'Copy MD'}
          </button>
          <button
            onClick={downloadMarkdown}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-border rounded-lg
                       font-mono text-sm text-dim hover:text-ink hover:border-dim transition-colors"
          >
            <Download size={13} />
            Download
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 max-w-3xl mx-auto w-full px-8 py-12">
        <ReportViewer markdown={data.report_final} citations={data.citations} />

        {/* Reference list */}
        {citationEntries.length > 0 && (
          <section className="mt-12 pt-8 border-t border-border">
            <h2 className="font-mono text-xs text-muted uppercase tracking-wider mb-5">References</h2>
            <ol className="flex flex-col gap-3">
              {citationEntries.map(([id, meta], i) => (
                <li key={id} className="flex gap-3 text-sm">
                  <span className="font-mono text-muted shrink-0">[{i + 1}]</span>
                  <div>
                    <p className="font-sans text-ink">{meta.source_title || meta.source_url}</p>
                    {meta.source_url && (
                      <a
                        href={meta.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-xs text-blue hover:underline"
                      >
                        {meta.source_url}
                      </a>
                    )}
                    {meta.page_number !== null && meta.page_number !== undefined && (
                      <span className="font-mono text-xs text-muted ml-2">p. {meta.page_number}</span>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </div>
  )
}
