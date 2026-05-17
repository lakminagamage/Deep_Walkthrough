'use client'

import { useEffect, useReducer } from 'react'
import { API_BASE } from '@/lib/utils'
import type { AgentState, SessionEvent, StreamState } from '@/types/session'

// ── Reducer ───────────────────────────────────────────────────────────────────

type Action =
  | { type: 'ADD_EVENT';   event: SessionEvent }
  | { type: 'SNAP_STATE';  state: AgentState }
  | { type: 'SET_HITL';    gate: 'plan' | 'sources'; payload: unknown }
  | { type: 'CLEAR_HITL' }
  | { type: 'COMPLETE';    reportId: string }
  | { type: 'ERROR';       message: string }

const initial: StreamState = {
  events:      [],
  latestState: null,
  pendingGate: null,
  hitlPayload: null,
  reportId:    null,
  complete:    false,
  error:       null,
}

function reducer(s: StreamState, a: Action): StreamState {
  switch (a.type) {
    case 'ADD_EVENT':  return { ...s, events: [...s.events, a.event] }
    case 'SNAP_STATE': return { ...s, latestState: a.state }
    case 'SET_HITL':   return { ...s, pendingGate: a.gate, hitlPayload: a.payload }
    case 'CLEAR_HITL': return { ...s, pendingGate: null,  hitlPayload: null }
    case 'COMPLETE':   return { ...s, complete: true, reportId: a.reportId }
    case 'ERROR':      return { ...s, error: a.message }
    default:           return s
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useSessionStream(sessionId: string) {
  const [state, dispatch] = useReducer(reducer, initial)

  useEffect(() => {
    if (!sessionId) return
    const es = new EventSource(`${API_BASE}/api/session/${sessionId}/stream`)

    es.onmessage = (e) => {
      const event = JSON.parse(e.data) as SessionEvent

      // Ignore infrastructure non-events.
      if (event.type === 'heartbeat' || event.type === 'done') return

      dispatch({ type: 'ADD_EVENT', event })

      if (event.type === 'state_snapshot') {
        dispatch({ type: 'SNAP_STATE', state: event.state })
      } else if (event.type === 'hitl_interrupt') {
        dispatch({ type: 'SET_HITL', gate: event.gate, payload: event.payload })
      } else if (event.type === 'session_complete') {
        dispatch({ type: 'COMPLETE', reportId: event.report_id })
        es.close()
      } else if (event.type === 'error') {
        dispatch({ type: 'ERROR', message: event.message })
        if (!event.recoverable) es.close()
      }
    }

    es.onerror = () => {
      dispatch({ type: 'ERROR', message: 'SSE connection lost' })
      es.close()
    }

    return () => es.close()
  }, [sessionId])

  const resumeSession = async (gate: string, decision: object) => {
    await fetch(`${API_BASE}/api/session/${sessionId}/resume`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ gate, decision }),
    })
    dispatch({ type: 'CLEAR_HITL' })
  }

  return { ...state, resumeSession }
}
