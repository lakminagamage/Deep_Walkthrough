'use client'

import { useState } from 'react'
import { Loader } from 'lucide-react'
import type { ResearchPlan } from '@/types/session'

interface Props {
  payload: unknown
  resumeSession: (gate: string, decision: object) => Promise<void>
}

export default function HITLPlanApproval({ payload, resumeSession }: Props) {
  const plan = (payload as { plan?: ResearchPlan })?.plan
  const [questions, setQuestions]   = useState<string[]>(plan?.sub_questions ?? [])
  const [editing, setEditing]       = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const submit = async (action: 'approve' | 'edit' | 'reject') => {
    setSubmitting(true)
    try {
      const decision =
        action === 'edit'
          ? { action, plan: { sub_questions: questions, approved: false } }
          : { action }
      await resumeSession('plan', decision)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-5 p-6 h-full overflow-y-auto">
      <div className="border-b border-amber/30 pb-4">
        <p className="font-mono text-xs text-amber uppercase tracking-wider mb-1">Gate 1 — Plan Approval</p>
        <p className="font-sans text-base text-dim">Review the research plan before retrieval begins.</p>
      </div>

      <div className="flex flex-col gap-3">
        {questions.map((q, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="font-mono text-sm text-muted mt-1 shrink-0">{i + 1}.</span>
            {editing ? (
              <input
                value={q}
                onChange={e => setQuestions(prev => prev.map((v, j) => j === i ? e.target.value : v))}
                className="flex-1 bg-surface border border-border rounded-lg px-3 py-2
                           text-base text-ink font-sans focus:outline-none focus:border-blue"
              />
            ) : (
              <p className="font-sans text-base text-ink leading-relaxed">{q}</p>
            )}
          </div>
        ))}
        {editing && (
          <button
            onClick={() => setQuestions(prev => [...prev, ''])}
            className="self-start text-sm font-mono text-blue hover:underline mt-1"
          >
            + Add sub-question
          </button>
        )}
      </div>

      <div className="flex gap-2 mt-auto pt-4 border-t border-border">
        {!editing ? (
          <>
            <ActionButton label="Approve" color="green" disabled={submitting} onClick={() => submit('approve')} loading={submitting} />
            <ActionButton label="Edit"    color="amber" disabled={submitting} onClick={() => setEditing(true)} />
            <ActionButton label="Reject"  color="red"   disabled={submitting} onClick={() => submit('reject')} />
          </>
        ) : (
          <>
            <ActionButton label="Submit Edits" color="blue"  disabled={submitting} onClick={() => submit('edit')} loading={submitting} />
            <ActionButton label="Cancel"       color="muted" disabled={submitting} onClick={() => { setEditing(false); setQuestions(plan?.sub_questions ?? []) }} />
          </>
        )}
      </div>
    </div>
  )
}

function ActionButton({
  label, color, disabled, onClick, loading,
}: {
  label: string; color: string; disabled?: boolean
  onClick: () => void; loading?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 px-4 py-2 text-sm font-mono rounded-lg border
                  transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                  border-${color}/40 text-${color} hover:bg-${color}/10`}
    >
      {loading && <Loader size={12} className="animate-spin" />}
      {label}
    </button>
  )
}
