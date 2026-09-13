import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { RiskOrb } from '../components/RiskOrb'
import { ClauseFilters, matchesFilter, type ClauseFilter } from '../components/ClauseCard'
import type { ClauseResult } from '../types/api'

// ---------------------------------------------------------------- API errors

describe('ApiError parsing', () => {
  beforeEach(() => { vi.restoreAllMocks() })

  it('maps backend error codes to friendly messages', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(
      JSON.stringify({ error: 'UNSUPPORTED_FILE_TYPE', message: 'raw message', request_id: 'r1' }),
      { status: 400 },
    )))
    const { api } = await import('../services/api')
    const err = await api.upload(new File([new Blob(['x'])], 'a.exe')).catch((e: Error) => e)
    expect((err as Error).message).toContain('not supported')
    expect((err as Error).message).not.toContain('raw message')
  })

  it('maps backend-offline (fetch rejection) to offline message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('network down') }))
    const { api } = await import('../services/api')
    const err = await api.stats().catch((e: Error) => e)
    expect((err as Error).message).toContain('offline')
  })
})

// ------------------------------------------------------------------- RiskOrb

describe('RiskOrb labels', () => {
  beforeEach(() => {
    // force reduced motion so the counter renders its value immediately in jsdom
    vi.stubGlobal('matchMedia', vi.fn().mockImplementation((q: string) => ({
      matches: q.includes('reduce'), media: q,
      addEventListener: vi.fn(), removeEventListener: vi.fn(),
    })))
  })

  it('exposes score, level and findings accessibly', async () => {
    render(<RiskOrb score={58} level="MEDIUM" findings={3} />)
    const orb = screen.getByRole('img')
    expect(orb).toHaveAttribute('aria-label', 'Overall risk score 58 of 100, level MEDIUM, 3 findings')
    expect(await screen.findByText('58')).toBeInTheDocument()
    expect(screen.getByText('MEDIUM')).toBeInTheDocument()
  })

  it('handles null score', () => {
    render(<RiskOrb score={null} level={null} />)
    expect(screen.getByText('0')).toBeInTheDocument()
  })
})

// ------------------------------------------------------------ clause filters

function clause(partial: Partial<ClauseResult>): ClauseResult {
  return { clause_type: 'x', found: true, confidence: 0.9, text: 't', start_char: 0,
           end_char: 1, risk_level: null, risk_reason: null, uncertain: false, ...partial }
}

describe('clause filter behavior', () => {
  const clauses: ClauseResult[] = [
    clause({ clause_type: 'a', found: true, risk_level: 'HIGH' }),
    clause({ clause_type: 'b', found: true, risk_level: 'MEDIUM' }),
    clause({ clause_type: 'c', found: true, risk_level: 'INFO' }),
    clause({ clause_type: 'd', found: false }),
  ]

  it('filters correctly by category', () => {
    expect(clauses.filter((c) => matchesFilter(c, 'all'))).toHaveLength(4)
    expect(clauses.filter((c) => matchesFilter(c, 'high')).map((c) => c.clause_type)).toEqual(['a'])
    expect(clauses.filter((c) => matchesFilter(c, 'medium')).map((c) => c.clause_type)).toEqual(['b'])
    expect(clauses.filter((c) => matchesFilter(c, 'info')).map((c) => c.clause_type)).toEqual(['c'])
    expect(clauses.filter((c) => matchesFilter(c, 'not_found')).map((c) => c.clause_type)).toEqual(['d'])
  })

  it('renders filter chips with counts and switches selection', async () => {
    const counts: Record<ClauseFilter, number> = { all: 4, high: 1, medium: 1, low: 0, info: 1, not_found: 1 }
    let current: ClauseFilter = 'all'
    const { rerender } = render(
      <ClauseFilters value={current} onChange={(f) => { current = f; rerender(
        <ClauseFilters value={current} onChange={(n) => { current = n }} counts={counts} />) }}
        counts={counts} />,
    )
    expect(screen.getByRole('tab', { name: /All/ })).toHaveAttribute('aria-selected', 'true')
    await userEvent.click(screen.getByRole('tab', { name: /High Risk/ }))
    expect(current).toBe('high')
  })
})

// -------------------------------------------------------------- empty states

describe('history empty state', () => {
  it('renders an inviting empty history (no fake data)', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(
      JSON.stringify({ total: 0, page: 1, page_size: 10, items: [] }),
      { status: 200 },
    )))
    const { ContractsPage } = await import('../pages/ContractsPage')
    render(<MemoryRouter><ContractsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Your history is empty')).toBeInTheDocument())
    expect(screen.getByText(/Analyzed contracts will be listed here/)).toBeInTheDocument()
  })
})

// ----------------------------------------------------------- offline state

describe('backend offline state', () => {
  it('shows offline error panel, not a crash', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline') }))
    const { IntelligencePage } = await import('../pages/IntelligencePage')
    render(<MemoryRouter><IntelligencePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('ContractIQ Engine Offline')).toBeInTheDocument())
  })
})
