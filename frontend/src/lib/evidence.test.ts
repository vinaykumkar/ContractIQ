import { describe, expect, it } from 'vitest'
import { segmentParagraphs, splitBlockForEvidence } from '../lib/evidence'

describe('evidence mapping', () => {
  const text = 'First paragraph here.\n\nSecond paragraph mentions the governing law of Texas.\n\nThird one.'

  it('segments paragraphs preserving original offsets', () => {
    const blocks = segmentParagraphs(text)
    expect(blocks).toHaveLength(3)
    expect(blocks[1].text).toBe('Second paragraph mentions the governing law of Texas.')
    expect(text.slice(blocks[1].start, blocks[1].start + blocks[1].text.length)).toBe(blocks[1].text)
    expect(blocks[2].start).toBe(text.indexOf('Third one.'))
  })

  it('splits oversized blocks on line boundaries', () => {
    const long = Array.from({ length: 300 }, (_, i) => `line ${i}`).join('\n')
    const blocks = segmentParagraphs(long, 1000)
    expect(blocks.length).toBeGreaterThan(1)
    for (const b of blocks) expect(b.text.length).toBeLessThanOrEqual(1000)
    // concatenation reconstructs the original
    const rebuilt = blocks.map((b) => b.text).join('')
    expect(rebuilt).toBe(long)
  })

  it('splits a block around the active evidence range', () => {
    const text = 'The parties agree that the governing law is Delaware for all disputes.'
    const blocks = segmentParagraphs(text)
    const start = text.indexOf('governing law is Delaware')
    const end = start + 'governing law is Delaware'.length
    const segs = splitBlockForEvidence(blocks[0], { start, end })
    const active = segs.filter((s) => s.highlight === 'active')
    expect(active).toHaveLength(1)
    expect(active[0].text).toBe('governing law is Delaware')
    expect(segs[0].highlight).toBe('none')
    expect(segs[segs.length - 1].highlight).toBe('none')
  })

  it('marks other clause ranges as dim when not active', () => {
    const text = 'Alpha agrees. Beta agrees too.'
    const blocks = segmentParagraphs(text)
    const dim = { start: 0, end: 'Alpha agrees.'.length }
    const segs = splitBlockForEvidence(blocks[0], null, [dim])
    expect(segs[0].highlight).toBe('dim')
  })

  it('clips ranges that fall outside the block', () => {
    const blocks = segmentParagraphs('Only one short block.')
    const segs = splitBlockForEvidence(blocks[0], { start: 500, end: 600 })
    expect(segs).toHaveLength(1)
    expect(segs[0].highlight).toBe('none')
  })
})
