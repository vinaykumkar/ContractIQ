import type { ReactNode } from 'react'
import { motion } from 'framer-motion'

/** Soft organic empty state with an inline SVG glyph (no stock art). */
export function EmptyState({ title, hint, glyph, children }: { title: string; hint?: string; glyph?: ReactNode; children?: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="flex flex-col items-center justify-center gap-4 py-16 text-center"
      role="status"
    >
      <div className="relative flex h-20 w-20 items-center justify-center">
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-aqua/20 via-lavender/15 to-coral/15 blur-md" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-ink-600 bg-ink-850">
          {glyph ?? (
            <svg viewBox="0 0 24 24" className="h-7 w-7 text-mist" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
              <path d="M6 3h9l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
              <path d="M14 3v5h5M9 13h6M9 17h4" />
            </svg>
          )}
        </div>
      </div>
      <p className="font-display text-lg text-ivory">{title}</p>
      {hint && <p className="max-w-sm text-sm leading-relaxed text-mist">{hint}</p>}
      {children}
    </motion.div>
  )
}
