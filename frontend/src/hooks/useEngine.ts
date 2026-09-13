/** Shared hooks: backend connectivity + simple async data fetching. */
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../services/api'
import type { Health } from '../types/api'

export type EngineState = 'checking' | 'online' | 'offline'

/**
 * Backend health tracking.
 * - checks on load
 * - polls at a calm interval (30 s online)
 * - while OFFLINE rechecks more often (12 s) so the UI recovers on its own
 *   when the backend returns - never aggressive (no per-second polling)
 * - exposes recheck() for the manual "Retry now" button
 */
export function useEngineStatus(): {
  state: EngineState
  health: Health | null
  recheck: () => void
} {
  const [state, setState] = useState<EngineState>('checking')
  const [health, setHealth] = useState<Health | null>(null)
  const [nonce, setNonce] = useState(0)
  const stateRef = useRef<EngineState>('checking')
  stateRef.current = state

  const check = useCallback(async () => {
    try {
      const h = await api.health()
      setHealth(h)
      setState(h.database === 'ok' ? 'online' : 'offline')
    } catch {
      setHealth(null)
      setState('offline')
    }
  }, [])

  useEffect(() => {
    void check()
    // interval depends on state: calm when online, quicker recovery when offline
    const interval = stateRef.current === 'offline' ? 12_000 : 30_000
    const t = setInterval(() => void check(), interval)
    return () => clearInterval(t)
  }, [check, nonce, state])

  const recheck = useCallback(() => setNonce((n) => n + 1), [])

  return { state, health, recheck }
}

interface AsyncState<T> {
  data: T | null
  error: ApiError | null
  loading: boolean
  reload: () => void
}

/**
 * Minimal fetch-on-mount hook (avoided extra data libraries deliberately).
 * Stale-response prevention: a `cancelled` flag per effect run guarantees a
 * slower older response can never overwrite a newer one, and no state updates
 * happen after unmount. StrictMode's double-invoke only re-runs idempotent
 * GETs, which is safe.
 */
export function useAsyncData<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    loader()
      .then((d) => { if (!cancelled) { setData(d); setLoading(false) } })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof ApiError ? e : new ApiError(0, { error: 'UNKNOWN', message: String(e) }))
          setLoading(false)
        }
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  return { data, error, loading, reload: () => setNonce((n) => n + 1) }
}
