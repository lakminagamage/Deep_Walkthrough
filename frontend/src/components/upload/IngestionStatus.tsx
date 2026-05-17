'use client'

import { CheckCircle, Circle, Loader, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface IngestJob {
  id: string
  name: string
  status: 'uploading' | 'embedding' | 'stored' | 'error'
  docId?: string
}

const STATUS_META: Record<
  IngestJob['status'],
  { label: string; color: string; Icon: React.ElementType; spin?: boolean }
> = {
  uploading: { label: 'Uploading',  color: 'text-blue',  Icon: Loader,       spin: true },
  embedding: { label: 'Embedding',  color: 'text-amber', Icon: Loader,       spin: true },
  stored:    { label: 'Stored',     color: 'text-green', Icon: CheckCircle                },
  error:     { label: 'Error',      color: 'text-red',   Icon: XCircle                    },
}

interface Props { jobs: IngestJob[] }

export default function IngestionStatus({ jobs }: Props) {
  if (!jobs.length) return null

  return (
    <div className="flex flex-col gap-1">
      <h3 className="font-mono text-xs text-muted uppercase tracking-wider mb-2">Queue</h3>
      {jobs.map(job => {
        const { label, color, Icon, spin } = STATUS_META[job.status]
        return (
          <div
            key={job.id}
            className="flex items-start gap-3 py-2.5 border-b border-border last:border-0"
          >
            <Icon
              size={14}
              className={cn(color, 'mt-0.5 shrink-0', spin && 'animate-spin')}
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm text-ink truncate font-sans">{job.name}</p>
              <p className={cn('text-xs font-mono mt-0.5', color)}>{label}</p>
              {job.docId && (
                <p className="text-xs font-mono text-muted truncate mt-0.5">{job.docId}</p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
