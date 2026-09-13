import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, FileText, Loader2, UploadCloud } from 'lucide-react'
import { api, ApiError } from '../services/api'
import { ErrorState } from '../components/ErrorState'

type Phase =
  | { k: 'idle' }
  | { k: 'dragging' }
  | { k: 'selected'; file: File }
  | { k: 'uploading'; file: File }
  | { k: 'analyzing'; file: File; contractId: string; filename: string; charCount: number | null; page_count: number | null; duplicateOf: string | null; startedAt: number }
  | { k: 'done'; analysisId: number; contractId: string }
  | { k: 'error'; message: string; code: string }

/** Honest process stages (visual workflow — not a fake percentage). */
const STAGES = [
  'Preparing contract',
  'Reading document',
  'Locating relevant clauses',
  'Extracting evidence',
  'Evaluating risk patterns',
  'Building intelligence report',
]

/** Honest elapsed wall-clock time (no fake progress percentages). */
function ElapsedTimer({ from }: { from: number }) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const secs = Math.max(0, Math.round((now - from) / 1000))
  return (
    <span className="font-mono text-xs text-mist" role="timer" aria-label="Elapsed analysis time">
      {secs}s elapsed
    </span>
  )
}

function AnalysisWorkflow({ stage }: { stage: number }) {
  return (
    <div className="space-y-3" aria-live="polite" aria-label="Analysis in progress">
      {STAGES.map((s, i) => {
        const done = i < stage
        const active = i === stage
        return (
          <motion.div
            key={s}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: done || active ? 1 : 0.35, x: 0 }}
            transition={{ duration: 0.35 }}
            className="flex items-center gap-3 text-sm"
          >
            <span className="flex h-5 w-5 items-center justify-center">
              {done ? (
                <CheckCircle2 className="h-4 w-4 text-mint" aria-hidden />
              ) : active ? (
                <Loader2 className="h-4 w-4 animate-spin text-aqua" aria-hidden />
              ) : (
                <span className="h-1.5 w-1.5 rounded-full bg-ink-600" aria-hidden />
              )}
            </span>
            <span className={active ? 'text-ivory' : done ? 'text-ivory-dim' : 'text-mist/70'}>{s}</span>
          </motion.div>
        )
      })}
    </div>
  )
}

export function AnalyzePage() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>({ k: 'idle' })
  const [stage, setStage] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const dragDepth = useRef(0)

  const advanceStages = useCallback((ms: number) => {
    const timers: number[] = []
    for (let i = 0; i < STAGES.length - 1; i++) {
      timers.push(window.setTimeout(() => setStage(i + 1), (ms / STAGES.length) * (i + 1)))
    }
    return timers
  }, [])

  const startFlow = useCallback(async (file: File) => {
    setPhase({ k: 'uploading', file })
    try {
      const contract = await api.upload(file)
      setPhase({
        k: 'analyzing', file, contractId: contract.id,
        filename: contract.filename, charCount: contract.character_count, page_count: contract.page_count,
        duplicateOf: contract.duplicate_of_id, startedAt: Date.now(),
      })
      const timers = advanceStages(9000) // visual pacing only; actual time depends on the document
      try {
        const res = await api.analyze(contract.id)
        timers.forEach(clearTimeout)
        setStage(STAGES.length - 1)
        setPhase({ k: 'done', analysisId: res.analysis_id, contractId: contract.id })
      } catch (err) {
        timers.forEach(clearTimeout)
        const e = err instanceof ApiError ? err : new ApiError(0, { message: String(err) })
        setPhase({ k: 'error', message: e.message, code: e.code })
      }
    } catch (err) {
      const e = err instanceof ApiError ? err : new ApiError(0, { message: String(err) })
      setPhase({ k: 'error', message: e.message, code: e.code })
    }
  }, [advanceStages])

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    dragDepth.current = 0
    const file = e.dataTransfer.files?.[0]
    if (file) startFlow(file)
    else setPhase({ k: 'idle' })
  }

  const dragging = phase.k === 'dragging'

  return (
    <div className="mx-auto max-w-3xl pt-6">
      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-1 font-display text-3xl text-ivory"
      >
        New Analysis
      </motion.h1>
      <p className="mb-8 text-sm text-mist">
        Upload a contract (PDF, DOCX or TXT) — the engine extracts clauses, evidence and risk patterns.
      </p>

      <AnimatePresence mode="wait">
        {/* ---------- drop zone / progress ---------- */}
        {phase.k === 'idle' || phase.k === 'dragging' || phase.k === 'selected' ? (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            onDragOver={(e) => { e.preventDefault(); if (phase.k !== 'dragging') setPhase({ k: 'dragging' }) }}
            onDragEnter={(e) => { e.preventDefault(); dragDepth.current++; setPhase({ k: 'dragging' }) }}
            onDragLeave={(e) => { e.preventDefault(); dragDepth.current--; if (dragDepth.current <= 0) setPhase({ k: 'idle' }) }}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
            role="button"
            tabIndex={0}
            aria-label="Upload a contract: drag and drop or press Enter to browse"
            className={`relative flex min-h-[320px] cursor-pointer flex-col items-center justify-center gap-5 overflow-hidden rounded-3xl border-2 border-dashed transition-colors ${
              dragging
                ? 'border-aqua/80 bg-aqua/5 shadow-[0_0_60px_rgba(86,196,201,0.12)]'
                : 'border-ink-600 bg-ink-900/40 hover:border-ink-600'
            }`}
          >
            <div className="absolute inset-0 bg-gradient-to-b from-aqua/0 via-aqua/[0.03] to-coral/[0.04]" aria-hidden />
            <motion.div
              animate={dragging ? { y: [-4, 4, -4] } : { y: 0 }}
              transition={dragging ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' } : {}}
              className="relative flex h-20 w-20 items-center justify-center rounded-full border border-ink-600 bg-ink-850"
            >
              <UploadCloud className="h-8 w-8 text-aqua" aria-hidden />
              <span className="absolute inset-0 rounded-full bg-aqua/10 blur-lg" aria-hidden />
            </motion.div>
            <div className="text-center">
              <p className="font-display text-xl text-ivory">
                {dragging ? 'Release to upload' : 'Drop your contract here'}
              </p>
              <p className="mt-2 text-xs text-mist">or click to browse · PDF, DOCX, TXT · up to 20 MB</p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0]
                e.target.value = ''
                if (f) void startFlow(f)
              }}
            />
          </motion.div>
        ) : phase.k === 'uploading' ? (
          <motion.div key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="ci-glass flex min-h-[320px] flex-col items-center justify-center gap-4 rounded-3xl">
            <Loader2 className="h-8 w-8 animate-spin text-aqua" aria-hidden />
            <p className="text-sm text-ivory">Uploading {phase.file.name}…</p>
          </motion.div>
        ) : phase.k === 'analyzing' ? (
          <motion.div key="analyzing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="ci-glass grid min-h-[320px] gap-8 rounded-3xl p-8 md:grid-cols-2">
            <div>
              <div className="flex items-center gap-3">
                <FileText className="h-8 w-8 text-aqua" aria-hidden />
                <div className="min-w-0">
                  <p className="truncate text-sm text-ivory">{phase.filename}</p>
                  <p className="text-xs text-mist">
                    {phase.charCount != null ? `${phase.charCount.toLocaleString()} chars` : ''}
                    {phase.page_count != null ? ` · ${phase.page_count} pages` : ''}
                  </p>
                </div>
              </div>
              <div className="mt-3"><ElapsedTimer from={phase.startedAt} /></div>
              {phase.duplicateOf && (
                <p className="mt-4 rounded-lg border border-lavender/30 bg-lavender/5 px-3 py-2 text-[11px] leading-relaxed text-lavender">
                  Note: identical text was uploaded before — this analysis is still running normally.
                </p>
              )}
              <p className="mt-6 text-xs leading-relaxed text-mist">
                The engine reads the document, asks the model for each enabled clause and scores
                risk patterns. This usually takes a few seconds to a couple of minutes depending on length.
              </p>
            </div>
            <AnalysisWorkflow stage={stage} />
          </motion.div>
        ) : phase.k === 'done' ? (
          <motion.div key="done" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
            className="ci-glass flex min-h-[320px] flex-col items-center justify-center gap-5 rounded-3xl p-8 text-center">
            <CheckCircle2 className="h-12 w-12 text-mint" aria-hidden />
            <p className="font-display text-2xl text-ivory">Analysis complete</p>
            <button
              onClick={() => navigate(`/contracts/${phase.contractId}`)}
              className="rounded-full bg-gradient-to-r from-aqua to-mint px-6 py-2.5 text-sm font-medium text-ink-950 transition-transform hover:scale-[1.03]"
            >
              Open intelligence report
            </button>
          </motion.div>
        ) : (
          <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex min-h-[320px] items-center justify-center">
            <ErrorState error={{ code: phase.code, message: phase.message } as ApiError}
              onRetry={() => setPhase({ k: 'idle' })} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
