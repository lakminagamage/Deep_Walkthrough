'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { API_BASE } from '@/lib/utils'
import DropZone from '@/components/upload/DropZone'
import IngestionStatus, { type IngestJob } from '@/components/upload/IngestionStatus'

export default function HomePage() {
  const router = useRouter()
  const [query, setQuery]             = useState('')
  const [docIds, setDocIds]           = useState<string[]>([])
  const [submitting, setSubmitting]   = useState(false)
  const [jobs, setJobs]               = useState<IngestJob[]>([])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/research`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ query: query.trim(), document_ids: docIds }),
      })
      const data = await res.json()
      router.push(`/session/${data.session_id}`)
    } finally {
      setSubmitting(false)
    }
  }

  const handleIngestComplete = (docId: string) => {
    setDocIds(prev => [...prev, docId])
  }

  return (
    <main className="min-h-screen bg-base flex flex-col">
      {/* Header */}
      <header className="border-b border-border px-8 py-4 flex items-center gap-3">
        <h1 className="font-sans text-base font-semibold text-ink tracking-tight">DeepWalkthrough</h1>
      </header>

      <div className="flex-1 flex gap-0 divide-x divide-border">
        {/* ── Left: Query form ───────────────────────────────────────────── */}
        <section className="flex-1 flex flex-col gap-7 p-10">
          <div>
            <h2 className="font-mono text-xs text-muted uppercase tracking-wider mb-2">
              Research Query
            </h2>
            <p className="text-dim text-base leading-relaxed">
              Ask a complex research question. The system will plan, retrieve, analyse, and
              synthesise a cited report.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={'e.g. "Evaluate the architectural trade-offs between video-centric generative world models and vector-quantized latent-state world action models in robotics. Specifically, investigate mechanisms to mitigate compounding predictive errors, resolve spatial-temporal inconsistencies in long-horizon reasoning, and overcome the scarcity of diverse real-world embodied interaction data."'}
              rows={6}
              className="w-full bg-surface border border-border rounded-lg px-4 py-3 text-ink
                         placeholder-muted font-sans text-base resize-none
                         focus:outline-none focus:border-blue transition-colors"
            />

            {docIds.length > 0 && (
              <div className="text-sm font-mono text-dim bg-raised rounded-lg px-3 py-2 border border-border">
                <span className="text-muted">Including </span>
                {docIds.length} document{docIds.length > 1 ? 's' : ''}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !query.trim()}
              className="self-start px-6 py-2.5 bg-blue text-white text-sm font-mono rounded-lg
                         hover:bg-blue/80 disabled:opacity-40 disabled:cursor-not-allowed
                         transition-colors"
            >
              {submitting ? 'Starting…' : 'Run Research →'}
            </button>
          </form>
        </section>

        {/* ── Right: Ingestion ───────────────────────────────────────────── */}
        <section className="w-[420px] flex flex-col gap-7 p-10">
          <div>
            <h2 className="font-mono text-xs text-muted uppercase tracking-wider mb-2">
              Knowledge Base
            </h2>
            <p className="text-dim text-base leading-relaxed">
              Upload PDFs or paste a URL to add documents to the retrieval store.
            </p>
          </div>

          <DropZone onIngestComplete={handleIngestComplete} addJob={setJobs} />
          <IngestionStatus jobs={jobs} />
        </section>
      </div>
    </main>
  )
}
