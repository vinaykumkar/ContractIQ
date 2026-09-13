import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, ArrowUpRight, UploadCloud } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { Stats, ContractListResponse } from '../types/api'
import { api } from '../services/api'
import { useAsyncData, useEngineStatus } from '../hooks/useEngine'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { RiskPill } from '../components/EngineStatus'
import { formatDateTime } from '../lib/evidence'

const DISCLAIMER_SHORT = 'AI-assisted analysis. Results should be reviewed by a qualified professional.'

function AnimatedNumber({ value }: { value: number }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    let raf = 0
    const start = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / 900)
      setDisplay(Math.round(value * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <span>{display}</span>
}

/** Segmented risk constellation ring (custom SVG — no chart library). */
function RiskConstellation({ dist }: { dist: Stats['risk_distribution'] }) {
  const total = Math.max(1, dist.LOW + dist.MEDIUM + dist.HIGH)
  const segs = [
    { label: 'HIGH', value: dist.HIGH, color: '#ff7264' },
    { label: 'MEDIUM', value: dist.MEDIUM, color: '#e8b566' },
    { label: 'LOW', value: dist.LOW, color: '#86dcc0' },
  ]
  const R = 54
  const C = 2 * Math.PI * R
  let acc = 0
  return (
    <div className="flex items-center gap-5">
      <svg viewBox="0 0 130 130" className="h-28 w-28 -rotate-90" aria-hidden>
        <circle cx="65" cy="65" r={R} fill="none" stroke="#222835" strokeWidth="10" opacity="0.6" />
        {segs.map((s) => {
          const frac = s.value / total
          const dash = `${frac * C} ${C}`
          const offset = -acc * C
          acc += frac
          return (
            <motion.circle
              key={s.label}
              cx="65" cy="65" r={R} fill="none"
              stroke={s.color} strokeWidth="10" strokeLinecap="butt"
              strokeDasharray={dash}
              initial={{ strokeDashoffset: offset - 30, opacity: 0 }}
              animate={{ strokeDashoffset: offset, opacity: 1 }}
              transition={{ duration: 0.9, ease: 'easeOut' }}
            />
          )
        })}
      </svg>
      <div className="space-y-2">
        {segs.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-xs">
            <span className="h-2 w-2 rounded-full" style={{ background: s.color }} aria-hidden />
            <span className="w-16 text-mist">{s.label}</span>
            <span className="font-mono text-ivory">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function OverviewPage() {
  const { state: engine } = useEngineStatus()
  const stats = useAsyncData<Stats>(() => api.stats(), [])
  const recent = useAsyncData<ContractListResponse>(() => api.listContracts({ page_size: 5 }), [])

  if (stats.error) return <ErrorState error={stats.error} onRetry={stats.reload} />

  const s = stats.data
  const recentItems = recent.data?.items ?? []

  return (
    <div className="pt-4">
      {/* hero */}
      <section className="relative overflow-hidden rounded-3xl px-6 py-12 text-center md:py-16">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
        >
          <h1 className="font-display text-4xl tracking-wide text-ivory md:text-5xl">
            Contract<span className="bg-gradient-to-r from-aqua via-mint to-lavender bg-clip-text text-transparent">IQ</span>
          </h1>
          <p className="mt-2 text-sm uppercase tracking-[0.3em] text-mist">AI Contract Intelligence &amp; Risk Analysis</p>
          <p className="mx-auto mt-5 max-w-xl text-sm leading-relaxed text-ivory-dim">
            Upload a contract and let the engine locate key clauses, extract the exact evidence,
            and surface heuristic risk patterns — with every finding traceable to its source text.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/analyze"
              className="group inline-flex items-center gap-2.5 rounded-full bg-gradient-to-r from-aqua to-mint px-6 py-3 text-sm font-medium text-ink-950 shadow-[0_0_36px_rgba(86,196,201,0.25)] transition-transform hover:scale-[1.03] active:scale-[0.98]"
            >
              <UploadCloud className="h-4 w-4" aria-hidden />
              Analyze a contract
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
            </Link>
          </div>
          {engine === 'offline' && (
            <p className="mt-4 text-xs text-coral">The engine is currently offline — start the backend to analyze documents.</p>
          )}
        </motion.div>
      </section>

      {/* statistic islands */}
      {stats.loading ? (
        <div className="mt-6 grid gap-4 md:grid-cols-3" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="ci-glass h-36 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : !s || (s.contracts_total === 0 && recentItems.length === 0) ? (
        <EmptyState
          title="No contracts yet"
          hint="Your analyses will appear here. Start by uploading a contract — the workspace walks you from upload to a full intelligence report."
        />
      ) : (
        <div className="mt-2 grid gap-4 md:grid-cols-3">
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="ci-glass rounded-2xl p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-mist">Contracts analyzed</p>
            <p className="mt-3 font-display text-4xl text-ivory">
              <AnimatedNumber value={s.completed_analyses} />
            </p>
            <p className="mt-1 text-xs text-mist">{s.contracts_total} uploaded in total</p>
            <div className="mt-4 flex items-center gap-3 border-t border-ink-700/60 pt-3 text-xs text-mist">
              <span>avg engine time</span>
              <span className="font-mono text-ivory-dim">
                {s.avg_processing_ms != null ? `${(s.avg_processing_ms / 1000).toFixed(1)} s` : '—'}
              </span>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} className="ci-glass rounded-2xl p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-mist">Risk constellation</p>
            <div className="mt-3">
              <RiskConstellation dist={s.risk_distribution} />
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }} className="ci-glass rounded-2xl p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-mist">Clauses detected</p>
            <p className="mt-3 font-display text-4xl text-ivory">{s.clauses_detected_total}</p>
            <p className="mt-1 text-xs text-mist">across all completed analyses</p>
            <div className="mt-4 flex flex-wrap gap-1.5 border-t border-ink-700/60 pt-3">
              <span className="rounded-full bg-coral/10 px-2 py-0.5 font-mono text-[10px] text-coral">{s.risk_distribution.HIGH} high</span>
              <span className="rounded-full bg-amber/10 px-2 py-0.5 font-mono text-[10px] text-amber">{s.risk_distribution.MEDIUM} medium</span>
              <span className="rounded-full bg-mint/10 px-2 py-0.5 font-mono text-[10px] text-mint">{s.risk_distribution.LOW} low</span>
            </div>
          </motion.div>
        </div>
      )}

      {/* recent activity */}
      {recentItems.length > 0 && (
        <section className="mt-8" aria-label="Recent activity">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-medium uppercase tracking-[0.2em] text-mist">Recent activity</h2>
            <Link to="/contracts" className="inline-flex items-center gap-1 text-xs text-aqua hover:text-mint">
              All contracts <ArrowUpRight className="h-3 w-3" aria-hidden />
            </Link>
          </div>
          <div className="space-y-2">
            {recentItems.map((c, i) => (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
              >
                <Link
                  to={`/contracts/${c.id}`}
                  className="ci-glass group flex items-center gap-4 rounded-xl px-4 py-3 transition-colors hover:ring-1 hover:ring-aqua/40"
                >
                  <span className="rounded-lg bg-ink-800 px-2 py-1 font-mono text-[10px] uppercase text-ivory-dim">
                    {c.file_type}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm text-ivory">{c.filename}</span>
                  {c.latest_analysis?.overall_risk_level && <RiskPill level={c.latest_analysis.overall_risk_level} size="sm" />}
                  <span className="hidden text-xs text-mist sm:block">{formatDateTime(c.created_at)}</span>
                  <ArrowUpRight className="h-4 w-4 text-mist opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
                </Link>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      <p className="mt-10 text-center text-[11px] text-mist/60">{DISCLAIMER_SHORT}</p>
    </div>
  )
}
