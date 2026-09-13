import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, FileSearch, Landmark, Scale, ShieldAlert, ShieldCheck } from 'lucide-react'
import type { Analysis } from '../types/api'
import { EmptyState } from './EmptyState'
import { RiskPill } from './EngineStatus'

/** Key entities panel — structured tokens, not a table. */
export function EntityPanel({ entities }: { entities: Analysis['entities'] }) {
  const items: Array<{ label: string; value: string | null; icon: ReactNode }> = [
    { label: 'Document', value: entities.document_name, icon: <FileSearch className="h-3.5 w-3.5" aria-hidden /> },
    { label: 'Parties', value: entities.parties, icon: <Landmark className="h-3.5 w-3.5" aria-hidden /> },
    { label: 'Agreement date', value: entities.agreement_date, icon: null },
    { label: 'Effective date', value: entities.effective_date, icon: null },
    { label: 'Expiration', value: entities.expiration_date, icon: null },
    { label: 'Governing law', value: entities.governing_law, icon: <Scale className="h-3.5 w-3.5" aria-hidden /> },
  ]
  const present = items.filter((i) => i.value)
  return (
    <section aria-label="Key entities">
      <h3 className="mb-3 text-xs font-medium uppercase tracking-[0.2em] text-mist">Key entities</h3>
      {present.length === 0 ? (
        <p className="text-xs text-mist/70">No entities confidently extracted.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {present.map(({ label, value, icon }, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              className="ci-glass max-w-full rounded-xl px-3 py-2"
            >
              <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-mist">
                {icon}
                {label}
              </div>
              <div className="mt-0.5 truncate text-xs text-ivory" title={value ?? undefined}>{value}</div>
            </motion.div>
          ))}
        </div>
      )}
    </section>
  )
}

/** Risk findings list with severity treatment (icon + label, not color-only). */
export function RiskFindingsPanel({ analysis }: { analysis: Analysis }) {
  const scored = analysis.risk_findings.filter((f) => !f.uncertain && (f.weight ?? 0) > 0)
  const uncertain = analysis.risk_findings.filter((f) => f.uncertain)
  const informational = analysis.risk_findings.filter((f) => (f.weight ?? 0) === 0 && !f.uncertain)

  if (analysis.risk_findings.length === 0) {
    return <EmptyState title="No risk findings" hint="The heuristic risk engine had nothing to flag on this contract." />
  }

  const icons: Record<string, ReactNode> = {
    HIGH: <ShieldAlert className="h-3.5 w-3.5" aria-hidden />,
    MEDIUM: <AlertTriangle className="h-3.5 w-3.5" aria-hidden />,
    LOW: <ShieldCheck className="h-3.5 w-3.5" aria-hidden />,
    INFO: <Scale className="h-3.5 w-3.5" aria-hidden />,
  }

  const Finding = ({ f, delay }: { f: Analysis['risk_findings'][number]; delay: number }) => (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.35, ease: 'easeOut' }}
      className="ci-glass rounded-xl p-3.5"
    >
      <div className="flex items-center gap-2">
        <span className={`flex h-6 w-6 items-center justify-center rounded-full ${
          f.severity === 'HIGH' ? 'bg-coral/15 text-coral'
          : f.severity === 'MEDIUM' ? 'bg-amber/15 text-amber'
          : 'bg-mint/15 text-mint'
        }`}>{icons[f.severity ?? 'INFO']}</span>
        <RiskPill level={f.severity} size="sm" />
        <span className="font-mono text-[10px] text-mist/70">+{f.weight}</span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-ivory-dim">{f.reason}</p>
      {f.evidence && (
        <p className="mt-1.5 truncate font-legal text-[11px] italic text-mist" title={f.evidence}>
          “{f.evidence}”
        </p>
      )}
    </motion.div>
  )

  return (
    <section aria-label="Risk findings" className="space-y-2">
      <h3 className="text-xs font-medium uppercase tracking-[0.2em] text-mist">Risk findings</h3>
      {scored.map((f, i) => <Finding key={f.rule_id} f={f} delay={i * 0.06} />)}
      {uncertain.length > 0 && (
        <p className="rounded-lg border border-amber/25 bg-amber/5 px-3 py-2 text-[11px] leading-relaxed text-amber/90">
          {uncertain.length} low-confidence indication{uncertain.length === 1 ? '' : 's'} excluded from the score.
        </p>
      )}
      {informational.length > 0 && (
        <p className="px-1 text-[11px] text-mist/70">
          + {informational.length} informational entr{informational.length === 1 ? 'y' : 'ies'} (not scored).
        </p>
      )}
    </section>
  )
}
