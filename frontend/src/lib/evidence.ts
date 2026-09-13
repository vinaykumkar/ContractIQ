/**
 * Evidence mapping: paragraph segmentation + character-offset highlighting.
 * Pure functions (unit-tested) so the viewer stays simple and efficient.
 */

export interface TextBlock {
  /** block content in the ORIGINAL text */
  text: string
  /** original char offset where this block starts */
  start: number
}

/** Split text into paragraph blocks, keeping original offsets. Blank runs
 *  between paragraphs are attached to the preceding block's tail. */
export function segmentParagraphs(text: string, maxBlockChars = 4000): TextBlock[] {
  const blocks: TextBlock[] = []
  const parts = text.split(/\n\s*\n/)
  let offset = 0
  for (const part of parts) {
    // skip the whitespace separator that the split consumed
    const remainder = text.slice(offset)
    offset += remainder.length - remainder.trimStart().length
    if (part.length > maxBlockChars) {
      // split very long paragraphs on line boundaries to bound DOM node size
      let pos = 0
      while (pos < part.length) {
        let end = Math.min(pos + maxBlockChars, part.length)
        const nl = part.lastIndexOf('\n', end)
        if (nl > pos) end = nl + 1
        blocks.push({ text: part.slice(pos, end), start: offset + pos })
        pos = end
      }
    } else {
      blocks.push({ text: part, start: offset })
    }
    offset += part.length
  }
  return blocks.filter((b) => b.text.length > 0)
}

export interface RenderSegment {
  text: string
  /** original offset of this segment's first char */
  start: number
  /** true when inside the highlighted evidence range */
  highlight: 'none' | 'active' | 'dim'
}

/** Split ONE block into render segments for the given evidence ranges.
 *  `active` range is highlighted strongly; other clause ranges dimly. */
export function splitBlockForEvidence(
  block: TextBlock,
  active: { start: number; end: number } | null,
  dimRanges: Array<{ start: number; end: number }> = [],
): RenderSegment[] {
  const blockEnd = block.start + block.text.length
  const cuts = new Set<number>([block.start, blockEnd])
  const push = (s: number, e: number) => {
    if (e > block.start && s < blockEnd) {
      cuts.add(Math.max(s, block.start))
      cuts.add(Math.min(e, blockEnd))
    }
  }
  if (active) push(active.start, active.end)
  for (const r of dimRanges) push(r.start, r.end)

  const sorted = [...cuts].sort((a, b) => a - b)
  const segments: RenderSegment[] = []
  for (let i = 0; i < sorted.length - 1; i++) {
    const s = sorted[i]
    const e = sorted[i + 1]
    if (e <= s) continue
    const isActive = active !== null && s >= active.start && e <= active.end
    const isDim = !isActive && dimRanges.some((r) => s >= r.start && e <= r.end)
    segments.push({ text: block.text.slice(s - block.start, e - block.start), start: s, highlight: isActive ? 'active' : isDim ? 'dim' : 'none' })
  }
  return segments
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
