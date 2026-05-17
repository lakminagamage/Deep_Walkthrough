'use client'

import { useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { CitationMeta } from './CitationTooltip'
import CitationTooltip from './CitationTooltip'

const UUID_RE = /\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]/g

interface Props {
  markdown: string | undefined | null
  citations: Record<string, CitationMeta>
}

export default function ReportViewer({ markdown, citations }: Props) {
  const chunkIndex = useCallback((): Map<string, number> => {
    const map = new Map<string, number>()
    let i = 1
    for (const match of (markdown ?? '').matchAll(UUID_RE)) {
      const id = match[1]
      if (!map.has(id)) map.set(id, i++)
    }
    return map
  }, [markdown])()

  const renderWithCitations = (text: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = []
    let last = 0
    for (const match of text.matchAll(UUID_RE)) {
      const id   = match[1]
      const idx  = match.index ?? 0
      if (idx > last) parts.push(text.slice(last, idx))
      parts.push(
        <CitationTooltip
          key={`${id}-${idx}`}
          index={chunkIndex.get(id) ?? 0}
          chunkId={id}
          meta={citations[id]}
        />
      )
      last = idx + match[0].length
    }
    if (last < text.length) parts.push(text.slice(last))
    return parts
  }

  return (
    <div className="prose-report">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p className="font-sans text-base text-ink leading-relaxed mb-4">
              {processChildren(children, renderWithCitations)}
            </p>
          ),
          h1: ({ children }) => (
            <h1 className="font-sans text-xl font-bold text-ink mt-8 mb-3 border-b border-border pb-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="font-sans text-lg font-semibold text-ink mt-6 mb-2">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="font-mono text-sm font-semibold text-dim uppercase tracking-wide mt-5 mb-2">
              {children}
            </h3>
          ),
          li: ({ children }) => (
            <li className="font-sans text-base text-ink ml-5 mb-1.5 list-disc leading-relaxed">
              {processChildren(children, renderWithCitations)}
            </li>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-ink">{children}</strong>
          ),
          code: ({ children }) => (
            <code className="font-mono text-sm bg-raised text-amber px-1.5 py-0.5 rounded-md">
              {children}
            </code>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-blue pl-5 text-dim italic my-4 leading-relaxed">
              {children}
            </blockquote>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  )
}

function processChildren(
  children: React.ReactNode,
  render: (t: string) => React.ReactNode[]
): React.ReactNode {
  if (typeof children === 'string') return render(children)
  if (Array.isArray(children)) {
    return children.flatMap((c, i) =>
      typeof c === 'string' ? render(c).map((n, j) => <span key={`${i}-${j}`}>{n}</span>) : [c]
    )
  }
  return children
}
