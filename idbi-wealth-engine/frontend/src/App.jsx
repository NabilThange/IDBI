import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { SessionProvider } from './context/SessionContext'
import ProfileSelection from './pages/ProfileSelection'
import GoalQuiz from './pages/GoalQuiz'
import Dashboard from './pages/Dashboard'
import BankApp from './pages/BankApp'
import ChatWidget from './components/ChatWidget'
import QrModal from './components/QrModal'
import { Agentation } from 'agentation'
import { DeviceMobileCamera } from '@phosphor-icons/react'
import { useIsMobile } from './lib/useIsMobile'

function App() {
  const [qrOpen, setQrOpen] = useState(false)
  const isMobile = useIsMobile()

  // Auto-open the QR modal on a visitor's first load (per browser session).
  // Honors the "don't show again" preference stored from a previous visit.
  // Skipped on mobile viewports — there's no point telling a phone user to
  // "open this on your phone".
  useEffect(() => {
    if (isMobile) return
    if (localStorage.getItem('idbi-qr-dont-show') === '1') return
    if (sessionStorage.getItem('idbi-qr-shown') === '1') return
    sessionStorage.setItem('idbi-qr-shown', '1')
    setQrOpen(true)
  }, [isMobile])

  return (
    <>
      <SessionProvider>
        <Router>
          <Routes>
            <Route path="/" element={<ProfileSelection />} />
            <Route path="/bank-app" element={<BankApp />} />
            <Route path="/quiz" element={<GoalQuiz />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          {/* Global draggable chat widget — visible on all pages when authenticated */}
          <ChatWidget />
        </Router>
      </SessionProvider>

      {/* Floating "open on mobile" button — re-opens the QR modal any time.
          Hidden on mobile viewports, where it would be redundant. */}
      {!isMobile && (
        <button
          onClick={() => setQrOpen(true)}
          aria-label="Open on your phone"
          title="Open on your phone"
          className="fixed bottom-6 left-6 z-[90] flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105 active:scale-95 hover:shadow-xl"
        >
          <DeviceMobileCamera size={24} weight="bold" />
        </button>
      )}

      {/* QR / mobile modal */}
      <QrModal open={qrOpen} onClose={() => setQrOpen(false)} />

      {import.meta.env.DEV && <Agentation />}
    </>
  )
}

export default App
