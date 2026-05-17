'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload } from 'lucide-react'
import { API_BASE, cn } from '@/lib/utils'
import type { IngestJob } from './IngestionStatus'

interface Props {
  onIngestComplete: (docId: string) => void
  addJob: React.Dispatch<React.SetStateAction<IngestJob[]>>
}

export default function DropZone({ onIngestComplete, addJob }: Props) {
  const [urlInput, setUrlInput] = useState('')

  const ingestFile = useCallback(
    async (file: File) => {
      const jobId = crypto.randomUUID()
      addJob(prev => [...prev, { id: jobId, name: file.name, status: 'uploading' }])

      const setStatus = (status: IngestJob['status'], docId?: string) =>
        addJob(prev =>
          prev.map(j => (j.id === jobId ? { ...j, status, docId } : j))
        )

      try {
        const form = new FormData()
        form.append('file', file)
        setStatus('embedding')
        const res = await fetch(`${API_BASE}/api/ingest`, { method: 'POST', body: form })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        setStatus('stored', data.doc_id)
        onIngestComplete(data.doc_id)
      } catch (err) {
        setStatus('error')
        console.error(err)
      }
    },
    [addJob, onIngestComplete]
  )

  const onDrop = useCallback(
    (accepted: File[]) => accepted.forEach(ingestFile),
    [ingestFile]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  })

  const handleUrl = async () => {
    const url = urlInput.trim()
    if (!url) return
    const jobId = crypto.randomUUID()
    addJob(prev => [...prev, { id: jobId, name: url, status: 'uploading' }])
    setUrlInput('')

    const setStatus = (status: IngestJob['status'], docId?: string) =>
      addJob(prev => prev.map(j => (j.id === jobId ? { ...j, status, docId } : j)))

    try {
      const form = new FormData()
      form.append('url', url)
      setStatus('embedding')
      const res = await fetch(`${API_BASE}/api/ingest`, { method: 'POST', body: form })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setStatus('stored', data.doc_id)
      onIngestComplete(data.doc_id)
    } catch (err) {
      setStatus('error')
      console.error(err)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer transition-colors',
          isDragActive
            ? 'border-blue bg-blue/5 text-blue'
            : 'border-border text-muted hover:border-dim hover:text-dim'
        )}
      >
        <input {...getInputProps()} />
        <Upload size={22} />
        <p className="font-sans text-sm text-center leading-relaxed">
          {isDragActive ? 'Drop PDFs here…' : 'Drag & drop PDFs, or click to browse'}
        </p>
      </div>

      <div className="flex gap-2">
        <input
          type="url"
          value={urlInput}
          onChange={e => setUrlInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleUrl()}
          placeholder="https://example.com/article"
          className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm font-mono
                     text-ink placeholder-muted focus:outline-none focus:border-blue"
        />
        <button
          onClick={handleUrl}
          disabled={!urlInput.trim()}
          className="px-4 py-2 bg-surface border border-border rounded-lg text-sm font-mono
                     text-dim hover:text-ink hover:border-dim disabled:opacity-40 transition-colors"
        >
          Ingest
        </button>
      </div>
    </div>
  )
}
