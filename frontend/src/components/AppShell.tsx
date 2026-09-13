import { NavLink, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Gauge, LayoutDashboard, Sparkles, UploadCloud } from 'lucide-react'
import type { ReactNode } from 'react'
import { useEngineStatus } from '../hooks/useEngine'
import { AuroraBackground } from './AuroraBackground'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/analyze', label: 'New Analysis', icon: UploadCloud },
  { to: '/contracts', label: 'Contracts', icon: FileText },
  { to: '/intelligence', label: 'Intelligence', icon: Sparkles },
]

/** Compact floating navigation rail (not a giant sidebar). */
function FloatingNav() {
  const location = useLocation()
  return (
    <nav
      aria-label="Primary"
      className="ci-glass-strong fixed bottom-4 left-1/2 z-40 flex -translate-x-1/2 items-center gap-1 rounded-full px-2 py-1.5 md:bottom-auto md:left-6 md:top-1/2 md:-translate-x-0 md:-translate-y-1/2 md:flex-col"
    >
      {NAV.map(({ to, label, icon: Icon }) => {
        const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
        return (
          <NavLink
            key={to}
            to={to}
            aria-label={label}
            title={label}
            className={`relative flex h-10 w-10 items-center justify-center rounded-full transition-colors md:h-11 md:w-11 ${
              active ? 'text-ink-950' : 'text-mist hover:text-ivory'
            }`}
          >
            {active && (
              <motion.span
                layoutId="nav-active"
                className="absolute inset-0 rounded-full bg-gradient-to-br from-aqua to-mint"
                transition={{ type: 'spring', stiffness: 420, damping: 32 }}
              />
            )}
            <Icon className="relative z-10 h-[18px] w-[18px]" aria-hidden />
          </NavLink>
        )
      })}
    </nav>
  )
}

function EngineIndicator() {
  const { state } = useEngineStatus()
  const dot = state === 'online' ? 'bg-mint' : state === 'checking' ? 'bg-amber' : 'bg-coral'
  const label = state === 'online' ? 'Engine online' : state === 'checking' ? 'Connecting…' : 'Engine offline'
  return (
    <div className="flex items-center gap-2" role="status" aria-label={label}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot} ${state !== 'checking' ? 'animate-pulse' : ''}`} aria-hidden />
      <span className="font-mono text-[10px] uppercase tracking-widest text-mist">{label}</span>
    </div>
  )
}

/** Application shell: aurora background, floating rail, top bar, outlet. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <AuroraBackground />
      <header className="flex items-center justify-between px-5 py-4 md:px-10">
        <a href="/" className="flex items-center gap-2.5" aria-label="ContractIQ home">
          <Gauge className="h-5 w-5 text-aqua" aria-hidden />
          <span className="font-display text-lg tracking-wide text-ivory">
            Contract<span className="text-aqua">IQ</span>
          </span>
        </a>
        <EngineIndicator />
      </header>
      <FloatingNav />
      <main className="mx-auto w-full max-w-6xl px-5 pb-28 md:px-10 md:pl-28">{children}</main>
      <footer className="px-5 pb-6 text-center text-[11px] leading-relaxed text-mist/60 md:px-10">
        ContractIQ provides AI-assisted contract analysis. Results should be reviewed by a qualified professional.
      </footer>
    </div>
  )
}
