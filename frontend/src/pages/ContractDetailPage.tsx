import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, FileText, Loader2 } from 'lucide-react'
import { api, ApiError } from '../services/api'
import { useAsyncData } from '../hooks/useEngine'
import { ErrorState } from '../components/ErrorState'
import { EmptyState } from '../components/EmptyState'
import { RiskOrb } from '../components/RiskOrb'
import { ClauseIntelligenceMap } from '../components/ClauseIntelligenceMap'
import { DocumentViewer } from '../components/DocumentViewer'
import { ClauseCard, ClauseFilters, matchesFilter, type ClauseFilter } from '../components/ClauseCard'
import { EntityPanel, RiskFindingsPanel } from '../components/IntelPanels'
import { PlayCircle } from 'lucide-react'
import type { Analysis, Contract, RawText } from '../types/api'
import { formatDateTime } from '../lib/evidence'

type MobileTab = 'document' | 'intelligence'

function counts(clauses: Analysis['clauses']): Record<ClauseFilter, number> {
  const counts: Record<ClauseFilter, number> = { all: clauses.length, high: 0, medium: 0, low: 0, info: 0, not_found: 0 }
  for (const c of clauses) {
    if (!c.found) counts.not_found++
    else if (c.risk_level === 'HIGH') counts.high++
    else if (c.risk_level === 'MEDIUM') counts.medium++
    else if (c.risk_level === 'INFO') counts.info++
    else counts.low++
  }
  return counts
}

function Workspace({
  contractId, analysis, text,
}: {
  contractId: string
  analysis: Analysis
  text: string | null
}) {
  const [activeClause, setActiveClause] = useState<string | null>(null)
  const [filter, setFilter] = useState<ClauseFilter>('all')
  const [mobileTab, setMobileTab] = useState<MobileTab>('document')
  const filterCounts = useMemo(() => counts(analysis.clauses), [analysis.clauses])
  const visibleClauses = useMemo(
    () => analysis.clauses.filter((c) => matchesFilter(c, filter)),
    [analysis.clauses, filter],
  )
  const findingCount = analysis.risk_findings.filter((f) => !f.uncertain && (f.weight ?? 0) > 0).length
  const notFoundCount = analysis.clauses.filter((c) => !c.found).length

  const focusClause = (label: string) => {
    setActiveClause(label)
    setMobileTab('document')
  }

  const intelligence = (
    <div className="space-y-5">
      <div className="flex flex-col items-center rounded-2xl bg-ink-900/50 py-6 ring-1 ring-ink-700/60">
        <RiskOrb score={analysis.overall_risk.score} level={analysis.overall_risk.level} findings={findingCount} />
      </div>

      <div className="rounded-2xl bg-ink-900/50 p-4 ring-1 ring-ink-700/60">
        <ClauseIntelligenceMap
          clauses={analysis.clauses}
          analyzing={false}
          onSelect={focusClause}
          selected={activeClause}
        />
      </div>

      <EntityPanel entities={analysis.entities} />

      <section aria-label="Clause findings">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-[0.2em] text-mist">Clauses</h3>
        <ClauseFilters value={filter} onChange={setFilter} counts={filterCounts} />
        <div className="mt-3 max-h-[520px] space-y-2 overflow-y-auto pr-1">
          {visibleClauses.length === 0 ? (
            <EmptyState title="Nothing in this filter" hint="Try a different filter to see other clause results." />
          ) : (
            visibleClauses.map((c) => (
              <ClauseCard key={c.clause_type} clause={c} active={activeClause === c.clause_type} onFocus={focusClause} />
            ))
          )}
        </div>
        {notFoundCount > 0 && (
          <p className="mt-3 px-1 text-[11px] leading-relaxed text-mist/70">
            {notFoundCount} clause type{notFoundCount === 1 ? '' : 's'} not found with sufficient confidence —
            nothing is claimed without evidence.
          </p>
        )}
      </section>

      <RiskFindingsPanel analysis={analysis} />

      <p className="rounded-xl border border-ink-700/60 px-3 py-2 text-center text-[10px] leading-relaxed text-mist/70">
        {analysis.disclaimer ?? 'AI-assisted analysis. Results should be reviewed by a qualified professional.'}
      </p>
    </div>
  )

  return (
    <div className="lg:flex lg:items-start lg:gap-6">
      {/* document column */}
      <div className={`min-w-0 flex-1 ${mobileTab === 'document' ? '' : 'hidden lg:block'}`}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="truncate font-display text-lg text-ivory" title={analysis.entities.document_name ?? undefined}>
            {analysis.entities.document_name ?? 'Contract document'}
          </h2>
          <span className="font-mono text-[10px] uppercase tracking-widest text-mist">
            {text ? `${text.length.toLocaleString()} chars` : ''}
          </span>
        </div>
        {text === null ? (
          <EmptyState
            title="Document text not available"
            hint="The original text was not stored for this contract. Enable text retention to use evidence highlighting."
          />
        ) : (
          <DocumentViewer text={text} clauses={analysis.clauses} activeClause={activeClause} />
        )}
      </div>

      {/* intelligence rail (desktop) */}
      <aside className="hidden w-[400px] shrink-0 lg:block" aria-label="Intelligence rail">
        {intelligence}
      </aside>

      {/* mobile bottom sheet */}
      <div className="fixed inset-x-0 bottom-14 z-30 lg:hidden">
        <div className="mx-4 overflow-hidden rounded-2xl">
          {mobileTab === 'intelligence' && (
            <div className="ci-glass-strong max-h-[62vh] overflow-y-auto rounded-2xl p-4 pb-6">
              {intelligence}
            </div>
          )}
          <div className="mt-2 grid grid-cols-2 gap-1 rounded-full bg-ink-800/95 p-1 ring-1 ring-ink-600 backdrop-blur">
            {(['document', 'intelligence'] as MobileTab[]).map((t) => (
              <button
                key={t}
                onClick={() => setMobileTab(t)}
                aria-pressed={mobileTab === t}
                className={`rounded-full py-2 text-xs font-medium capitalize transition-colors ${
                  mobileTab === t ? 'bg-gradient-to-r from-aqua to-mint text-ink-950' : 'text-mist'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>
      <span className="sr-only">contract {contractId}</span>
    </div>
  )
}

/** Full analysis workspace. Reconstructs saved analyses (never re-analyzes on
 *  open) and recovers from every backend status: COMPLETED / FAILED /
 *  ANALYZING (polled) / READY (Analyze action, request-locked). */
export function ContractDetailPage() {
  const { id = '' } = useParams()
  const contractState = useAsyncData<Contract>(() => api.getContract(id), [id])
  const analysis = useAsyncData<Analysis | null>(
    () => api.getAnalysis(id).catch((e: ApiError) => {
      if (e.code === 'ANALYSIS_FAILURE' || e.status === 500) return null // not analyzed yet / failed
      throw e
    }),
    [id],
  )
  const text = useAsyncData<RawText | null>(
    () => api.getRawText(id).catch((e: ApiError) => {
      if (e.code === 'RAW_TEXT_UNAVAILABLE') return null
      throw e
    }),
    [id],
  )

  const [analyzing, setAnalyzing] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)
  const analyzingRef = useRef(false)
  analyzingRef.current = analyzing

  const reloadAll = useCallback(() => {
    contractState.reload(); analysis.reload(); text.reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // if the backend reports ANALYZING (e.g. started in another tab), poll calmly
  // until it resolves, then reload the workspace from the source of truth
  const status = contractState.data?.status
  useEffect(() => {
    if (status !== 'ANALYZING') return
    const t = setInterval(() => {
      void api.getContract(id).then((c) => {
        if (c.status !== 'ANALYZING') reloadAll()
      }).catch(() => { /* offline: keep waiting */ })
    }, 4000)
    return () => clearInterval(t)
  }, [status, id, reloadAll])

  const startAnalysis = useCallback(async () => {
    if (analyzingRef.current) return // request lock: never double-submit
    setAnalyzing(true)
    setActionError(null)
    try {
      await api.analyze(id)
    } catch (e) {
      setActionError(e instanceof ApiError ? e : new ApiError(0, { message: String(e) }))
    } finally {
      setAnalyzing(false)
      reloadAll()
    }
  }, [id, reloadAll])

  if (contractState.error) return <ErrorState error={contractState.error} onRetry={contractState.reload} />
  if (analysis.error) return <ErrorState error={analysis.error} onRetry={analysis.reload} />
  if (text.error) return <ErrorState error={text.error} onRetry={text.reload} />
  if (contractState.loading) {
    return (
      <div className="flex items-center gap-3 py-24 text-mist" role="status">
        <Loader2 className="h-5 w-5 animate-spin text-aqua" aria-hidden /> Loading contract…
      </div>
    )
  }
  const c = contractState.data
  if (!c) {
    return <ErrorState error={contractState.error} onRetry={contractState.reload} title="Contract not found" />
  }
  const a = analysis.data

  return (
    <div className="pt-6">
      <Link to="/contracts" className="mb-4 inline-flex items-center gap-1.5 text-xs text-mist hover:text-aqua">
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> All contracts
      </Link>

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <FileText className="h-5 w-5 text-aqua" aria-hidden />
        <h1 className="min-w-0 truncate font-display text-2xl text-ivory">{c.filename}</h1>
        <span className="rounded-full bg-ink-800 px-2 py-0.5 font-mono text-[10px] uppercase text-ivory-dim">{c.file_type}</span>
        <span className="text-xs text-mist">{formatDateTime(c.created_at)}</span>
        {c.duplicate_of_id && (
          <span className="rounded-full border border-lavender/40 px-2 py-0.5 text-[10px] text-lavender"
            title={`Identical text was already uploaded as contract ${c.duplicate_of_id.slice(0, 8)}…`}>
            duplicate
          </span>
        )}
      </div>

      {actionError && (
        <div className="mb-4">
          <ErrorState error={actionError} onRetry={() => { setActionError(null); void startAnalysis() }} />
        </div>
      )}

      {status === 'ANALYZING' && (
        <div className="mb-5 flex items-center gap-3 rounded-xl border border-aqua/30 bg-aqua/5 px-4 py-3 text-sm text-aqua" role="status">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Analysis in progress — this page updates automatically when it finishes.
        </div>
      )}

      {status === 'FAILED' && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-coral/30 bg-coral/5 px-4 py-3 text-sm text-coral">
          <span>The last analysis failed. {c.latest_analysis?.error_message ?? ''}</span>
          <button
            onClick={() => void startAnalysis()}
            disabled={analyzing}
            className="inline-flex items-center gap-1.5 rounded-full border border-coral/40 px-3 py-1 text-xs transition-colors hover:bg-coral/10 disabled:opacity-50"
          >
            {analyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <PlayCircle className="h-3.5 w-3.5" aria-hidden />}
            {analyzing ? 'Analyzing…' : 'Retry analysis'}
          </button>
        </div>
      )}

      {analysis.loading && !analyzing ? (
        <div className="flex items-center gap-3 py-24 text-mist" role="status">
          <Loader2 className="h-5 w-5 animate-spin text-aqua" aria-hidden /> Loading analysis…
        </div>
      ) : a && a.status === 'COMPLETED' ? (
        <Workspace contractId={id} analysis={a} text={text.data?.text ?? null} />
      ) : status === 'READY' || status === 'FAILED' || status === 'UPLOADED' ? (
        <EmptyState
          title={status === 'FAILED' ? 'No completed analysis' : 'Not analyzed yet'}
          hint="Run the engine to extract clauses, evidence and risk patterns for this contract."
        >
          <button
            onClick={() => void startAnalysis()}
            disabled={analyzing}
            className="mt-2 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-aqua to-mint px-6 py-2.5 text-sm font-medium text-ink-950 transition-transform hover:scale-[1.03] disabled:opacity-50"
          >
            {analyzing
              ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              : <PlayCircle className="h-4 w-4" aria-hidden />}
            {analyzing ? 'Analyzing…' : 'Analyze contract'}
          </button>
        </EmptyState>
      ) : null}
    </div>
  )
}
