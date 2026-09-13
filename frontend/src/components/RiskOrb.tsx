import { motion, useReducedMotion } from 'framer-motion'
import { useEffect, useState } from 'react'

const RING_COLORS: Record<string, [string, string]> = {
  LOW: ['#86dcc0', '#56c4c9'],
  MEDIUM: ['#e8b566', '#ff9d64'],
  HIGH: ['#ff7264', '#d94f42'],
}

/** Animated counting number (respect reduced motion). */
function AnimatedNumber({ value }: { value: number }) {
  const reduce = useReducedMotion()
  const [display, setDisplay] = useState(reduce ? value : 0)
  useEffect(() => {
    if (reduce) { setDisplay(value); return }
    let raf = 0
    const start = performance.now()
    const from = 0
    const dur = 1100
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur)
      const eased = 1 - Math.pow(1 - p, 3)
      setDisplay(Math.round(from + (value - from) * eased))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value, reduce])
  return <span>{display}</span>
}

/**
 * RiskOrb — signature risk visualization.
 * Soft radial core + segmented arc; communicates score, level, findings.
 * Accessible: numeric score in the DOM, level as text, not color-only.
 */
export function RiskOrb({
  score,
  level,
  findings,
  size = 210,
}: {
  score: number | null
  level: string | null
  findings?: number
  size?: number
}) {
  const reduce = useReducedMotion()
  const value = score ?? 0
  const [c1, c2] = RING_COLORS[level ?? 'LOW'] ?? RING_COLORS.LOW
  const R = 88
  const SEGMENTS = 36
  const filled = Math.round((value / 100) * SEGMENTS)
  const gradId = `orb-grad-${level ?? 'none'}`

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Overall risk score ${value} of 100, level ${level ?? 'unknown'}${
        findings !== undefined ? `, ${findings} findings` : ''
      }`}
    >
      {/* glow core */}
      <div
        className="absolute inset-3 rounded-full opacity-25 blur-xl"
        style={{ background: `radial-gradient(circle, ${c1}88 0%, transparent 70%)` }}
        aria-hidden
      />
      <svg viewBox="0 0 220 220" width={size} height={size} aria-hidden className="relative">
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={c1} />
            <stop offset="100%" stopColor={c2} />
          </linearGradient>
        </defs>

        {/* track ring */}
        <circle cx="110" cy="110" r={R} fill="none" stroke="#222835" strokeWidth="7" opacity="0.7" />

        {/* segmented arc */}
        {Array.from({ length: SEGMENTS }, (_, i) => {
          const angle = (i / SEGMENTS) * 360 - 90
          const active = i < filled
          const x = 110 + R * Math.cos((angle * Math.PI) / 180)
          const y = 110 + R * Math.sin((angle * Math.PI) / 180)
          const x2 = 110 + R * Math.cos(((angle + 7.2) * Math.PI) / 180)
          const y2 = 110 + R * Math.sin(((angle + 7.2) * Math.PI) / 180)
          return (
            <motion.line
              key={i}
              x1={x} y1={y} x2={x2} y2={y2}
              stroke={active ? `url(#${gradId})` : '#2e3543'}
              strokeWidth={active ? 7 : 5}
              strokeLinecap="round"
              initial={reduce ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: reduce ? 0 : 0.15 + i * 0.022, duration: 0.18 }}
            />
          )
        })}

        {/* inner organic ring */}
        <motion.circle
          cx="110" cy="110" r={R - 16}
          fill="none"
          stroke={c1}
          strokeOpacity="0.18"
          strokeWidth="1.2"
          strokeDasharray="3 6"
          animate={reduce ? undefined : { rotate: 360 }}
          transition={{ duration: 90, repeat: Infinity, ease: 'linear' }}
          style={{ transformOrigin: '110px 110px' }}
        />
      </svg>

      {/* center readout */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="font-display text-5xl leading-none text-ivory">
          <AnimatedNumber value={value} />
        </div>
        <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.25em] text-mist">risk score</div>
        <div
          className="mt-2 rounded-full border px-3 py-0.5 font-mono text-xs uppercase tracking-widest"
          style={{ borderColor: `${c1}55`, color: c1, background: `${c1}14` }}
        >
          {level ?? '—'}
        </div>
        {findings !== undefined && (
          <div className="mt-1.5 text-[11px] text-mist">
            {findings} finding{findings === 1 ? '' : 's'}
          </div>
        )}
      </div>
    </div>
  )
}
