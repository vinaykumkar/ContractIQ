import { motion, useReducedMotion } from 'framer-motion'
import type { ClauseResult } from '../types/api'

/** Human-friendly names for clause labels. */
const LABELS: Record<string, string> = {
  document_name: 'Document Name',
  parties: 'Parties',
  agreement_date: 'Agreement Date',
  effective_date: 'Effective Date',
  expiration_date: 'Expiration Date',
  renewal_term: 'Renewal Term',
  governing_law: 'Governing Law',
  termination_for_convenience: 'Termination',
  non_compete: 'Non-Compete',
  exclusivity: 'Exclusivity',
  anti_assignment: 'Anti-Assignment',
  license_grant: 'License Grant',
  audit_rights: 'Audit Rights',
  cap_on_liability: 'Liability Cap',
  insurance: 'Insurance',
}

export function clauseDisplayName(label: string): string {
  return LABELS[label] ?? label.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

const LEVEL_COLORS: Record<string, string> = {
  HIGH: '#ff7264',
  MEDIUM: '#e8b566',
  LOW: '#86dcc0',
  INFO: '#b7a7e8',
}

interface MapNode {
  label: string
  x: number
  y: number
}

/** Deterministic organic node placement (two rings around the hub). */
function layout(nodes: string[]): MapNode[] {
  const inner = nodes.slice(0, Math.ceil(nodes.length / 2))
  const outer = nodes.slice(inner.length)
  const placed: MapNode[] = []
  inner.forEach((label, i) => {
    const a = (i / inner.length) * 360 - 90
    placed.push({ label, x: 260 + 110 * Math.cos((a * Math.PI) / 180), y: 240 + 92 * Math.sin((a * Math.PI) / 180) })
  })
  outer.forEach((label, i) => {
    const a = ((i + 0.5) / outer.length) * 360 - 90
    placed.push({ label, x: 260 + 185 * Math.cos((a * Math.PI) / 180), y: 240 + 158 * Math.sin((a * Math.PI) / 180) })
  })
  return placed
}

/**
 * ClauseIntelligenceMap — ContractIQ's signature visual.
 * Central document node surrounded by clause nodes; connections breathe while
 * analyzing, nodes activate as clauses are found, risk colors the treatment.
 */
export function ClauseIntelligenceMap({
  clauses,
  analyzing,
  onSelect,
  selected,
}: {
  clauses: ClauseResult[] | null
  analyzing: boolean
  onSelect?: (label: string) => void
  selected?: string | null
}) {
  const reduce = useReducedMotion()
  const mapClauses = clauses ?? []
  const activeLabels = mapClauses.map((c) => c.clause_type)
  const nodes = layout(activeLabels.length ? activeLabels : [])
  const byLabel = new Map(mapClauses.map((c) => [c.clause_type, c]))

  return (
    <div className="relative w-full" aria-label="Clause intelligence map" role="img">
      <svg viewBox="0 0 520 480" className="w-full">
        <defs>
          <radialGradient id="cim-hub" cx="50%" cy="42%">
            <stop offset="0%" stopColor="#56c4c9" stopOpacity="0.55" />
            <stop offset="55%" stopColor="#3aa88b" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#12151c" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* connections */}
        {nodes.map((n, i) => {
          const c = byLabel.get(n.label)
          const found = analyzing ? true : Boolean(c?.found)
          const color = analyzing
            ? '#56c4c9'
            : found
              ? (LEVEL_COLORS[c?.risk_level ?? 'INFO'] ?? '#56c4c9')
              : '#2e3543'
          return (
            <motion.line
              key={`link-${n.label}`}
              x1={260} y1={240} x2={n.x} y2={n.y}
              stroke={color}
              strokeWidth={found ? 1.4 : 0.8}
              strokeOpacity={found ? 0.65 : 0.3}
              strokeDasharray={analyzing ? '4 5' : undefined}
              initial={reduce ? false : { pathLength: 0, opacity: 0 }}
              animate={
                reduce
                  ? { opacity: 1 }
                  : analyzing
                    ? { opacity: [0.25, 0.8, 0.25], pathLength: 1 }
                    : { opacity: 1, pathLength: 1 }
              }
              transition={
                reduce
                  ? { duration: 0.3 }
                  : analyzing
                    ? { duration: 2.2, repeat: Infinity, delay: i * 0.12 }
                    : { duration: 0.9, delay: 0.12 + i * 0.05 }
              }
            />
          )
        })}

        {/* hub */}
        <circle cx={260} cy={240} r={78} fill="url(#cim-hub)" />
        <motion.circle
          cx={260} cy={240} r={46}
          fill="#12151c"
          stroke="#56c4c9"
          strokeOpacity={analyzing ? 0.9 : 0.55}
          strokeWidth="1.4"
          animate={analyzing && !reduce ? { strokeOpacity: [0.4, 0.95, 0.4] } : {}}
          transition={{ duration: 2.4, repeat: analyzing ? Infinity : 0, ease: 'easeInOut' }}
        />
        <text x={260} y={236} textAnchor="middle" className="fill-ivory" fontSize="13" fontFamily="var(--font-display)">
          Contract
        </text>
        <text x={260} y={254} textAnchor="middle" className="fill-mist" fontSize="9" letterSpacing="2">
          {analyzing ? 'ANALYZING' : `${mapClauses.filter((c) => c.found).length}/${mapClauses.length} CLAUSES`}
        </text>

        {/* clause nodes */}
        {nodes.map((n, i) => {
          const c = byLabel.get(n.label)
          const found = analyzing ? false : Boolean(c?.found)
          const baseColor = analyzing ? '#56c4c9' : found ? (LEVEL_COLORS[c?.risk_level ?? 'INFO'] ?? '#86dcc0') : '#2e3543'
          const isSelected = selected === n.label
          return (
            <motion.g
              key={`node-${n.label}`}
              initial={reduce ? false : { opacity: 0, scale: 0.4 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: reduce ? 0 : 0.3 + i * 0.07, duration: 0.5, ease: 'easeOut' }}
              style={{ transformOrigin: `${n.x}px ${n.y}px`, cursor: onSelect && found ? 'pointer' : 'default' }}
              onClick={() => found && onSelect?.(n.label)}
              role="button"
              aria-label={`${clauseDisplayName(n.label)}: ${analyzing ? 'analyzing' : found ? `found, risk ${c?.risk_level ?? 'INFO'}` : 'not found'}`}
              tabIndex={found && onSelect ? 0 : -1}
              onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && found) { e.preventDefault(); onSelect?.(n.label) } }}
            >
              {found && !analyzing && (
                <motion.circle
                  cx={n.x} cy={n.y} r={26}
                  fill="none"
                  stroke={baseColor}
                  strokeOpacity={0.35}
                  strokeWidth="1"
                  animate={reduce ? undefined : { scale: [1, 1.2, 1], strokeOpacity: [0.4, 0.05, 0.4] }}
                  transition={{ duration: 3.4, repeat: Infinity, delay: i * 0.3 }}
                  style={{ transformOrigin: `${n.x}px ${n.y}px` }}
                />
              )}
              <circle
                cx={n.x} cy={n.y} r={isSelected && found ? 22 : 18}
                fill={found ? `${baseColor}26` : '#181c25'}
                stroke={baseColor}
                strokeOpacity={found ? 0.9 : 0.4}
                strokeWidth={isSelected && found ? 2 : 1.1}
              />
              <text
                x={n.x} y={n.y + 38}
                textAnchor="middle"
                fontSize="9.5"
                letterSpacing="0.6"
                className={found ? 'fill-ivory' : 'fill-mist'}
                opacity={found ? 1 : 0.6}
              >
                {clauseDisplayName(n.label)}
              </text>
            </motion.g>
          )
        })}
      </svg>
      {analyzing && (
        <div className="absolute bottom-1 left-1/2 -translate-x-1/2 font-mono text-[10px] uppercase tracking-[0.25em] text-aqua/80">
          mapping clauses…
        </div>
      )}
    </div>
  )
}
