import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronLeft, ChevronRight, FileText, Search, Trash2 } from 'lucide-react'
import type { Contract, ContractListResponse, RiskLevel } from '../types/api'
import { api, ApiError } from '../services/api'
import { useAsyncData } from '../hooks/useEngine'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { RiskPill } from '../components/EngineStatus'
import { formatDateTime } from '../lib/evidence'

const STATUS_FILTERS = ['ALL', 'READY', 'COMPLETED', 'FAILED'] as const
const SORTS = [
  { value: 'created_at_desc', label: 'Newest first' },
  { value: 'created_at_asc', label: 'Oldest first' },
  { value: 'filename_asc', label: 'Name A–Z' },
] as const
const RISK_FILTERS = ['', 'HIGH', 'MEDIUM', 'LOW'] as const

export function ContractsPage() {
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<(typeof STATUS_FILTERS)[number]>('ALL')
  const [risk, setRisk] = useState<(typeof RISK_FILTERS)[number]>('')
  const [sort, setSort] = useState<(typeof SORTS)[number]['value']>('created_at_desc')
  const [page, setPage] = useState(1)
  const [deleting, setDeleting] = useState<string | null>(null)

  const list = useAsyncData<ContractListResponse>(
    () => api.listContracts({ page, page_size: 10, search: query, status: status === 'ALL' ? undefined : status, risk_level: risk || undefined, sort }),
    [query, status, risk, sort, page, deleting],
  )

  const onDelete = async (id: string) => {
    setDeleting(id)
    try {
      await api.deleteContract(id)
    } catch (e) {
      if (!(e instanceof ApiError)) throw e
    } finally {
      setDeleting(null)
      list.reload()
    }
  }

  const totalPages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1
  const items: Contract[] = list.data?.items ?? []
  const hasAny = (list.data?.total ?? 0) > 0 || query || status !== 'ALL' || risk

  return (
    <div className="pt-6">
      <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-1 font-display text-3xl text-ivory">
        Contracts
      </motion.h1>
      <p className="mb-6 text-sm text-mist">Your document history — reopen any analysis.</p>

      {/* filters */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <form
          className="relative"
          onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(search) }}
          role="search"
        >
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-mist" aria-hidden />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onBlur={() => { setPage(1); setQuery(search) }}
            placeholder="Search filenames…"
            aria-label="Search contracts by filename"
            className="w-56 rounded-full border border-ink-600 bg-ink-900/70 py-2 pl-9 pr-3 text-sm text-ivory placeholder:text-mist/60 focus:border-aqua/60 focus:outline-none"
          />
        </form>
        {STATUS_FILTERS.map((s) => (
          <button key={s} onClick={() => { setStatus(s); setPage(1) }}
            aria-pressed={status === s}
            className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-wider transition-colors ${
              status === s ? 'border-aqua/60 bg-aqua/10 text-aqua' : 'border-ink-600 text-mist hover:text-ivory-dim'
            }`}>
            {s}
          </button>
        ))}
        <select
          value={risk}
          onChange={(e) => { setRisk(e.target.value as (typeof RISK_FILTERS)[number]); setPage(1) }}
          aria-label="Filter by risk level"
          className="rounded-full border border-ink-600 bg-ink-900 px-3 py-1 text-[11px] text-mist focus:border-aqua/60 focus:outline-none"
        >
          {RISK_FILTERS.map((r) => <option key={r} value={r}>{r ? `Risk: ${r}` : 'Any risk'}</option>)}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as typeof sort)}
          aria-label="Sort contracts"
          className="rounded-full border border-ink-600 bg-ink-900 px-3 py-1 text-[11px] text-mist focus:border-aqua/60 focus:outline-none"
        >
          {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {list.error ? (
        <ErrorState error={list.error} onRetry={list.reload} />
      ) : list.loading ? (
        <div className="space-y-2" aria-busy="true">
          {[0, 1, 2].map((i) => <div key={i} className="ci-glass h-16 animate-pulse rounded-xl" />)}
        </div>
      ) : items.length === 0 ? (
        hasAny ? (
          <EmptyState title="No matching contracts" hint="Try a different search, status or risk filter." />
        ) : (
          <EmptyState
            title="Your history is empty"
            hint="Analyzed contracts will be listed here so you can reopen their intelligence reports anytime."
          />
        )
      ) : (
        <div className="space-y-2">
          {items.map((c, i) => (
            <motion.div key={c.id}
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
              <div className="ci-glass group flex items-center gap-4 rounded-xl px-4 py-3 transition-colors hover:ring-1 hover:ring-aqua/40">
                <Link to={`/contracts/${c.id}`} className="flex min-w-0 flex-1 items-center gap-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ink-800">
                    <FileText className="h-4 w-4 text-aqua" aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-ivory">{c.filename}</span>
                    <span className="block text-xs text-mist">
                      {c.file_type.toUpperCase()} · {formatDateTime(c.created_at)}
                      {c.latest_analysis?.processing_ms != null &&
                        ` · ${(c.latest_analysis.processing_ms / 1000).toFixed(1)}s`}
                    </span>
                  </span>
                  <span className="hidden shrink-0 sm:block">
                    {c.latest_analysis?.overall_risk_level
                      ? <RiskPill level={c.latest_analysis.overall_risk_level as RiskLevel} size="sm" />
                      : <span className="font-mono text-[10px] uppercase tracking-wider text-mist/70">{c.status}</span>}
                  </span>
                </Link>
                <button
                  onClick={() => void onDelete(c.id)}
                  disabled={deleting === c.id}
                  aria-label={`Delete ${c.filename}`}
                  className="shrink-0 rounded-full p-2 text-mist opacity-0 transition-all hover:bg-coral/10 hover:text-coral focus-visible:opacity-100 group-hover:opacity-100 disabled:opacity-30"
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </button>
              </div>
            </motion.div>
          ))}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-4">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}
                aria-label="Previous page"
                className="rounded-full border border-ink-600 p-1.5 text-mist disabled:opacity-30 hover:text-ivory">
                <ChevronLeft className="h-4 w-4" aria-hidden />
              </button>
              <span className="font-mono text-xs text-mist">{page} / {totalPages}</span>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                aria-label="Next page"
                className="rounded-full border border-ink-600 p-1.5 text-mist disabled:opacity-30 hover:text-ivory">
                <ChevronRight className="h-4 w-4" aria-hidden />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
