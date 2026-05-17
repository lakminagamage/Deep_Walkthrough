'use client'

import { useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface CitationMeta {
  source_url:   string
  source_title: string
  page_number:  number | null
  chunk_text:   string
}

interface Props {
  index: number
  chunkId: string
  meta: CitationMeta | undefined
}

export default function CitationTooltip({ index, chunkId, meta }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <span className="relative inline-block">
      <sup
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="cursor-pointer text-blue font-mono text-xs font-bold px-0.5
                   hover:text-blue/80 transition-colors"
      >
        [{index}]
      </sup>

      {open && (
        <span
          className={cn(
            'absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50',
            'w-80 bg-raised border border-border rounded-xl shadow-xl p-4',
            'flex flex-col gap-2 pointer-events-none'
          )}
        >
          {meta ? (
            <>
              <span className="font-sans text-sm text-ink font-semibold leading-snug">
                {meta.source_title || meta.source_url}
              </span>
              {meta.source_url && (
                <span className="font-mono text-xs text-blue truncate flex items-center gap-1">
                  <ExternalLink size={10} />
                  {meta.source_url.slice(0, 55)}
                </span>
              )}
              {meta.page_number !== null && meta.page_number !== undefined && (
                <span className="font-mono text-xs text-muted">p. {meta.page_number}</span>
              )}
              <span className="font-sans text-sm text-dim border-t border-border pt-2 leading-relaxed">
                {meta.chunk_text.slice(0, 220)}{meta.chunk_text.length > 220 ? '…' : ''}
              </span>
            </>
          ) : (
            <span className="font-mono text-xs text-muted">chunk: {chunkId.slice(0, 12)}…</span>
          )}
        </span>
      )}
    </span>
  )
}
