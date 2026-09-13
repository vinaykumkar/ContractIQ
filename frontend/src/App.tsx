import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { RefreshCw } from 'lucide-react'
import { AppShell } from './components/AppShell'
import { useEngineStatus } from './hooks/useEngine'
import { OverviewPage } from './pages/OverviewPage'
import { AnalyzePage } from './pages/AnalyzePage'
import { ContractsPage } from './pages/ContractsPage'
import { ContractDetailPage } from './pages/ContractDetailPage'
import { IntelligencePage } from './pages/IntelligencePage'

/** Offline banner with manual recheck — the UI recovers when the backend returns. */
function OfflineNotice({ hidden, onRetry }: { hidden: boolean; onRetry: () => void }) {
  if (hidden) return null
  return (
    <div className="mx-auto mb-2 max-w-6xl px-5 md:px-10 md:pl-28">
      <div className="flex items-center justify-center gap-3 rounded-xl border border-coral/30 bg-coral/5 px-4 py-2.5 text-center text-xs text-coral">
        <span>ContractIQ Engine Offline — start the backend (run_backend.bat) to upload and analyze contracts.</span>
        <button
          onClick={onRetry}
          className="inline-flex shrink-0 items-center gap-1 rounded-full border border-coral/40 px-2 py-0.5 text-[10px] uppercase tracking-wider transition-colors hover:bg-coral/10"
        >
          <RefreshCw className="h-3 w-3" aria-hidden /> Retry now
        </button>
      </div>
    </div>
  )
}

function ShellRoutes() {
  const { state, recheck } = useEngineStatus()
  return (
    <AppShell>
      <OfflineNotice hidden={state === 'online'} onRetry={recheck} />
      <AnimatePresence mode="wait">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/analyze" element={<AnalyzePage />} />
          <Route path="/contracts" element={<ContractsPage />} />
          <Route path="/contracts/:id" element={<ContractDetailPage />} />
          <Route path="/intelligence" element={<IntelligencePage />} />
          <Route path="*" element={<OverviewPage />} />
        </Routes>
      </AnimatePresence>
    </AppShell>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ShellRoutes />
    </BrowserRouter>
  )
}
