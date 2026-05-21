'use client'

import { useEffect, useRef, useState } from 'react'
import { ExternalLink, X } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface CitationMeta {
  source_url:   string
  source_title: string
  page_number:  number | null
  chunk_text:   string
}

interface Props {
  index:   number
  chunkId: string
  meta:    CitationMeta | undefined
}

export default function CitationTooltip({ index, chunkId, meta }: Props) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e: PointerEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [open])

  const isWebSource = Boolean(meta?.source_url)

  return (
    <span ref={containerRef} className="relative inline-block">
      <sup
        onClick={() => setOpen(v => !v)}
        className={cn(
          'cursor-pointer font-mono text-xs font-bold px-0.5 select-none transition-colors',
          open ? 'text-blue/60' : 'text-blue hover:text-blue/80'
        )}
      >
        [{index}]
      </sup>

      {open && (
        <span
          className={cn(
            'absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50',
            'w-96 bg-raised border border-border rounded-xl shadow-2xl',
            'flex flex-col pointer-events-auto'
          )}
          // Stop clicks inside the card from bubbling to the outside handler
          onPointerDown={e => e.stopPropagation()}
        >
          {/* Header */}
          <span className="flex items-start gap-2 px-4 pt-4 pb-3">
            <span className="flex-1 font-sans text-sm font-semibold text-ink leading-snug">
              {meta?.source_title || meta?.source_url || `Source ${index}`}
            </span>
            <button
              onClick={() => setOpen(false)}
              className="shrink-0 mt-0.5 text-muted hover:text-ink transition-colors"
              aria-label="Close"
            >
              <X size={13} />
            </button>
          </span>

          {/* Clickable link */}
          {isWebSource && (
            <a
              href={meta!.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mx-4 mb-3 font-mono text-xs text-blue hover:underline flex items-center gap-1.5 break-all"
            >
              <ExternalLink size={10} className="shrink-0 mt-px" />
              {meta!.source_url}
            </a>
          )}

          {meta?.page_number !== null && meta?.page_number !== undefined && (
            <span className="mx-4 mb-3 font-mono text-xs text-muted">
              p. {meta.page_number}
            </span>
          )}

          {/* Chunk text */}
          <span className="mx-4 mb-4 border-t border-border pt-3 block">
            <span className="font-mono text-xs text-muted uppercase tracking-wider block mb-1.5">
              Source excerpt
            </span>
            <span
              className="font-sans text-sm text-dim leading-relaxed block max-h-52 overflow-y-auto pr-1"
            >
              {meta?.chunk_text || `chunk id: ${chunkId}`}
            </span>
          </span>
        </span>
      )}
    </span>
  )
}
