import { Cpu, ShieldCheck, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import type { Health } from '../types/api'
import { EmptyState } from './EmptyState'

const DISCLAIMER =
  'ContractIQ provides AI-assisted contract analysis. Results should be reviewed by a qualified professional.'

/** Risk level pill that does not rely on color alone (icon + label). */
export function RiskPill({ level, size = 'md' }: { level: string | null | undefined; size?: 'sm' | 'md' }) {
  if (!level) return null
  const styles: Record<string, string> = {
    LOW: 'border-mint/40 bg-mint/10 text-mint',
    MEDIUM: 'border-amber/40 bg-amber/10 text-amber',
    HIGH: 'border-coral/40 bg-coral/10 text-coral',
    INFO: 'border-lavender/40 bg-lavender/10 text-lavender',
  }
  const icons: Record<string, string> = { LOW: '○', MEDIUM: '◎', HIGH: '▲', INFO: '·' }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono uppercase tracking-wider ${
        styles[level] ?? 'border-ink-600 text-mist'
      } ${size === 'sm' ? 'text-[10px]' : 'text-xs'}`}
    >
      <span aria-hidden>{icons[level] ?? '·'}</span>
      {level}
    </span>
  )
}

/** Intelligence / model info panel (EngineStatus). */
export function EngineStatus({ health }: { health: Health | null }) {
  if (!health) {
    return <EmptyState title="Engine status unknown" hint="Connect to the backend to see model information." />
  }
  const m = health.model
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <motion.div layout className="ci-glass rounded-2xl p-6">
        <div className="flex items-center gap-2 text-mist">
          <Sparkles className="h-4 w-4 text-lavender" aria-hidden />
          <h3 className="text-xs font-medium uppercase tracking-[0.2em]">Analysis model</h3>
        </div>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-mist">Availability</dt>
            <dd className={m.available ? 'text-mint' : 'text-coral'}>{m.available ? 'Ready' : 'Not set up'}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-mist">Model state</dt>
            <dd className="text-ivory">{m.state === 'fine_tuned' ? 'Fine-tuned on CUAD' : 'Pretrained baseline'}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-mist">Version</dt>
            <dd className="font-mono text-xs text-ivory-dim">{m.model_version ?? '—'}</dd>
          </div>
        </dl>
      </motion.div>

      <motion.div layout className="ci-glass rounded-2xl p-6">
        <div className="flex items-center gap-2 text-mist">
          <Cpu className="h-4 w-4 text-aqua" aria-hidden />
          <h3 className="text-xs font-medium uppercase tracking-[0.2em]">Runtime</h3>
        </div>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-mist">Compute device</dt>
            <dd className="font-mono text-xs uppercase text-ivory">{m.device}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-mist">API version</dt>
            <dd className="font-mono text-xs text-ivory-dim">{health.version}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-mist">Database</dt>
            <dd className={health.database === 'ok' ? 'text-mint' : 'text-coral'}>{health.database}</dd>
          </div>
        </dl>
      </motion.div>

      <motion.div layout className="ci-glass rounded-2xl p-6 md:col-span-2">
        <div className="flex items-center gap-2 text-mist">
          <ShieldCheck className="h-4 w-4 text-mint" aria-hidden />
          <h3 className="text-xs font-medium uppercase tracking-[0.2em]">Risk methodology</h3>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-ivory-dim">
          Clause extraction is performed by an AI model trained on the CUAD legal-contract dataset.
          Each finding carries its extraction confidence. The risk score is computed by transparent
          heuristic rules (never by the model) and reflects general contract patterns — not legal advice.
        </p>
        <p className="mt-3 border-t border-ink-700 pt-3 text-xs leading-relaxed text-mist">{DISCLAIMER}</p>
      </motion.div>
    </div>
  )
}
