import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { SessionProvider } from './context/SessionContext'
import ProfileSelection from './pages/ProfileSelection'
import GoalQuiz from './pages/GoalQuiz'
import Dashboard from './pages/Dashboard'
import BankApp from './pages/BankApp'
import ChatWidget from './components/ChatWidget'
import { Agentation } from 'agentation'

function App() {
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
      {import.meta.env.DEV && <Agentation />}
    </>
  )
}

export default App


