import { motion } from 'framer-motion'
import { AlertTriangle, RotateCcw, WifiOff } from 'lucide-react'
interface ErrorLike { code: string; message?: string; requestId?: string }

/** Human-friendly error panel using the backend's structured envelope. */
export function ErrorState({
  error,
  onRetry,
  title,
}: {
  error: ErrorLike | null
  onRetry?: () => void
  title?: string
}) {
  const offline = error?.code === 'BACKEND_OFFLINE' || error?.code === 'TIMEOUT'
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="ci-glass mx-auto flex max-w-md flex-col items-center gap-4 rounded-2xl px-8 py-10 text-center"
      role="alert"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-coral/10 text-coral">
        {offline ? <WifiOff className="h-5 w-5" aria-hidden /> : <AlertTriangle className="h-5 w-5" aria-hidden />}
      </div>
      <div>
        <p className="font-display text-lg text-ivory">{title ?? (offline ? 'ContractIQ Engine Offline' : 'Something went wrong')}</p>
        <p className="mt-2 text-sm leading-relaxed text-mist">
          {offline
            ? 'The analysis engine could not be reached. Start the backend (run_backend.bat) and try again.'
            : (error?.message ?? 'An unexpected error occurred.')}
        </p>
      </div>
      {error?.code === 'MODEL_UNAVAILABLE' && (
        <p className="rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-xs text-mist">
          Set up the analysis model once, then restart the engine.
        </p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-full border border-ink-600 px-4 py-2 text-sm text-ivory transition-colors hover:border-aqua/60 hover:text-aqua"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden /> Try again
        </button>
      )}
      {error?.requestId && (
        <p className="font-mono text-[10px] text-mist/60">ref {error.requestId}</p>
      )}
    </motion.div>
  )
}
