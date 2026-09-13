import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, ChevronDown, Copy, Minus, X } from 'lucide-react'
import type { ClauseResult } from '../types/api'
import { clauseDisplayName } from './ClauseIntelligenceMap'
import { RiskPill } from './EngineStatus'

/** Expandable clause result card. Clicking focuses the document evidence. */
export function ClauseCard({
  clause,
  active,
  onFocus,
}: {
  clause: ClauseResult
  active: boolean
  onFocus: (label: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const name = clauseDisplayName(clause.clause_type)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(clause.text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch { /* clipboard unavailable */ }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`ci-glass rounded-xl transition-shadow ${
        active ? 'ring-1 ring-aqua/70 shadow-[0_0_24px_rgba(86,196,201,0.15)]' : 'hover:ring-1 hover:ring-ink-600'
      }`}
    >
      <button
        className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left"
        onClick={() => { setOpen((o) => !o); if (clause.found) onFocus(clause.clause_type) }}
        aria-expanded={open}
      >
        <span
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] ${
            clause.found ? 'bg-mint/15 text-mint' : 'bg-ink-700 text-mist'
          }`}
          aria-hidden
        >
          {clause.found ? <Check className="h-3.5 w-3.5" /> : <Minus className="h-3.5 w-3.5" />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-ivory">{name}</span>
          {clause.found ? (
            <span className="block truncate text-xs text-mist">{clause.text.slice(0, 70) || '—'}</span>
          ) : (
            <span className="block text-xs text-mist/70">Not found in this contract</span>
          )}
        </span>
        {clause.found && (
          <span className="hidden shrink-0 font-mono text-[11px] text-ivory-dim sm:block">
            {(100 * (clause.confidence ?? 0)).toFixed(0)}%
          </span>
        )}
        {clause.found && clause.risk_level && clause.risk_level !== 'INFO' && <RiskPill level={clause.risk_level} size="sm" />}
        {clause.uncertain && (
          <span className="shrink-0 rounded-full border border-amber/40 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-amber">
            unsure
          </span>
        )}
        <ChevronDown className={`h-4 w-4 shrink-0 text-mist transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="border-t border-ink-700/70 px-4 pb-4 pt-3">
              {clause.found ? (
                <>
                  <p className="font-legal text-sm leading-relaxed text-ivory/85">{clause.text || '—'}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); void copy() }}
                      className="inline-flex items-center gap-1.5 rounded-full border border-ink-600 px-2.5 py-1 text-[11px] text-mist transition-colors hover:border-aqua/50 hover:text-aqua"
                    >
                      {copied ? <Check className="h-3 w-3" aria-hidden /> : <Copy className="h-3 w-3" aria-hidden />}
                      {copied ? 'Copied' : 'Copy evidence'}
                    </button>
                    {clause.found && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onFocus(clause.clause_type) }}
                        className="rounded-full border border-ink-600 px-2.5 py-1 text-[11px] text-mist transition-colors hover:border-aqua/50 hover:text-aqua"
                      >
                        Show in document
                      </button>
                    )}
                    <span className="font-mono text-[10px] text-mist/70">
                      confidence {(100 * (clause.confidence ?? 0)).toFixed(1)}%
                    </span>
                  </div>
                  {clause.risk_reason && (
                    <p className="mt-3 rounded-lg bg-ink-800/80 px-3 py-2 text-xs leading-relaxed text-ivory-dim">
                      {clause.risk_reason}
                    </p>
                  )}
                </>
              ) : (
                <p className="text-xs leading-relaxed text-mist">
                  {clauseDisplayName(clause.clause_type)} was not detected with sufficient confidence,
                  so nothing is claimed. {clause.risk_reason ?? ''}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export type ClauseFilter = 'all' | 'high' | 'medium' | 'low' | 'info' | 'not_found'

export const FILTER_LABELS: Record<ClauseFilter, string> = {
  all: 'All',
  high: 'High Risk',
  medium: 'Medium',
  low: 'Low Risk',
  info: 'Informational',
  not_found: 'Not Found',
}

export function matchesFilter(c: ClauseResult, f: ClauseFilter): boolean {
  switch (f) {
    case 'all': return true
    case 'not_found': return !c.found
    case 'high': return c.found && c.risk_level === 'HIGH'
    case 'medium': return c.found && c.risk_level === 'MEDIUM'
    case 'low': return c.found && (c.risk_level === 'LOW' || c.risk_level === null)
    case 'info': return c.found && c.risk_level === 'INFO'
  }
}

/** Segmented filter chips. */
export function ClauseFilters({
  value,
  onChange,
  counts,
}: {
  value: ClauseFilter
  onChange: (f: ClauseFilter) => void
  counts: Record<ClauseFilter, number>
}) {
  const keys = Object.keys(FILTER_LABELS) as ClauseFilter[]
  return (
    <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Clause filters">
      {keys.map((k) => (
        <button
          key={k}
          role="tab"
          aria-selected={value === k}
          onClick={() => onChange(k)}
          className={`rounded-full border px-3 py-1 text-[11px] transition-colors ${
            value === k
              ? 'border-aqua/60 bg-aqua/10 text-aqua'
              : 'border-ink-600 text-mist hover:border-ink-600/80 hover:text-ivory-dim'
          }`}
        >
          {FILTER_LABELS[k]}
          <span className="ml-1.5 font-mono text-[10px] opacity-70">{counts[k]}</span>
        </button>
      ))}
    </div>
  )
}

/** Small closed-card glyph used in list views. */
export function NotFoundGlyph() {
  return <X className="h-3 w-3" aria-label="not found" />
}
