import { useEffect, useMemo, useRef } from 'react'
import { motion } from 'framer-motion'
import type { ClauseResult } from '../types/api'
import { segmentParagraphs, splitBlockForEvidence } from '../lib/evidence'

/**
 * DocumentViewer — renders the parsed contract text efficiently.
 * Only the paragraphs overlapping the ACTIVE evidence range get highlighted
 * spans; every other paragraph renders as a single text node, so long
 * contracts stay cheap to render. Exact backend char offsets are used.
 */
export function DocumentViewer({
  text,
  clauses,
  activeClause,
  onSelectParagraph,
}: {
  text: string
  clauses: ClauseResult[]
  activeClause: string | null
  onSelectParagraph?: () => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const blocks = useMemo(() => segmentParagraphs(text), [text])

  const active = useMemo(() => {
    if (!activeClause) return null
    const c = clauses.find((x) => x.clause_type === activeClause)
    if (!c?.found || c.start_char === null || c.end_char === null) return null
    return { start: c.start_char, end: c.end_char }
  }, [clauses, activeClause])

  const dimRanges = useMemo(
    () =>
      clauses
        .filter((c) => c.found && c.clause_type !== activeClause && c.start_char !== null && c.end_char !== null)
        .map((c) => ({ start: c.start_char as number, end: c.end_char as number })),
    [clauses, activeClause],
  )

  // scroll the active evidence into view
  useEffect(() => {
    if (!active || !containerRef.current) return
    const marker = containerRef.current.querySelector('[data-active-evidence="true"]')
    marker?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [active?.start, active?.end]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      ref={containerRef}
      className="ci-doc relative max-h-[calc(100vh-230px)] min-h-[300px] overflow-y-auto rounded-2xl bg-ink-900/60 p-8 ring-1 ring-ink-700/70"
      onClick={onSelectParagraph}
    >
      {blocks.map((block, bi) => {
        const overlaps =
          (active && active.start < block.start + block.text.length && block.start < active.end) ||
          dimRanges.some((r) => r.start < block.start + block.text.length && block.start < r.end)
        if (!overlaps) {
          return <p key={bi}>{block.text}</p>
        }
        const segments = splitBlockForEvidence(block, active, dimRanges)
        return (
          <p key={bi}>
            {segments.map((seg, si) => {
              if (seg.highlight === 'none') return <span key={si}>{seg.text}</span>
              const isActive = seg.highlight === 'active'
              return (
                <mark
                  key={si}
                  data-active-evidence={isActive || undefined}
                  className={isActive ? 'ci-evidence' : 'ci-evidence-dim'}
                >
                  {isActive && (
                    <motion.span
                      layoutId="evidence-dot"
                      className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-aqua align-middle"
                      aria-hidden
                    />
                  )}
                  {seg.text}
                </mark>
              )
            })}
          </p>
        )
      })}
    </div>
  )
}
