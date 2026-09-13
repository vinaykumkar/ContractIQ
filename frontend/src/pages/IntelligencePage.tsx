import { useEngineStatus } from '../hooks/useEngine'
import { EngineStatus } from '../components/EngineStatus'
import { ErrorState } from '../components/ErrorState'
import { motion } from 'framer-motion'

/** Intelligence / model info page. */
export function IntelligencePage() {
  const { state, health } = useEngineStatus()
  return (
    <div className="pt-6">
      <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-1 font-display text-3xl text-ivory">
        Intelligence
      </motion.h1>
      <p className="mb-6 text-sm text-mist">Model status, runtime and methodology.</p>
      {state === 'offline' ? (
        <ErrorState error={{ code: 'BACKEND_OFFLINE', message: 'offline' }}
          title="ContractIQ Engine Offline"
        />
      ) : state === 'checking' ? (
        <div className="ci-glass h-64 animate-pulse rounded-2xl" aria-busy="true" />
      ) : (
        <EngineStatus health={health} />
      )}
    </div>
  )
}
