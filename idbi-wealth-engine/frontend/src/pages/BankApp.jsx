import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../context/SessionContext'
import { List as Menu, X, ArrowRight, TrendUp as TrendingUp, CreditCard, PaperPlaneRight as Send, Bank as Landmark, User, SignOut as LogOut } from '@phosphor-icons/react'
 
export default function BankApp() {
  const [drawerOpen, setDrawerOpen] = useState(false)
 
  const { profile, checkQuizStatus, clearSession, isAuthenticated } = useSession()
  const navigate = useNavigate()
 
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/')
    }
  }, [isAuthenticated, navigate])
 
  const handleWealthInsightClick = async () => {
    setDrawerOpen(false)
    try {
      const quizStatus = await checkQuizStatus()
      if (!quizStatus.quiz_completed || quizStatus.needs_refresh) {
        navigate('/quiz')
      } else {
        navigate('/dashboard')
      }
    } catch (err) {
      console.error('Error checking quiz status:', err)
      navigate('/dashboard')
    }
  }
 
  const handleLogout = async () => {
    await clearSession()
    navigate('/')
  }
 
  if (!profile) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-100">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-primary"></div>
      </div>
    )
  }
 
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none relative overflow-hidden">
      
      {/* Background glow effects for premium look */}
      <div className="absolute top-[-20%] left-[-25%] w-[80%] h-[80%] rounded-full bg-primary/5 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-25%] w-[80%] h-[80%] rounded-full bg-primary/5 blur-[120px] pointer-events-none" />
 
      {/* Top Header Bar */}
      <header className="bg-slate-900/40 backdrop-blur-md border-b border-slate-800/80 px-6 py-4 flex items-center justify-between z-30 sticky top-0">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setDrawerOpen(true)}
            className="p-2 -ml-2 rounded-xl text-slate-300 hover:text-slate-100 hover:bg-slate-800/50 active:scale-95 transition-all duration-200"
            aria-label="Open Menu"
          >
            <Menu className="w-6 h-6" />
          </button>
          
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-primary animate-pulse"></span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">IDBI NetBanking</span>
          </div>
        </div>
 
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex flex-col items-end">
            <span className="text-xs font-bold text-slate-200">{profile.name}</span>
            <span className="text-[10px] text-slate-400">{profile.occupation}</span>
          </div>
          <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center">
            <User className="w-4.5 h-4.5 text-slate-300" />
          </div>
        </div>
      </header>
 
      {/* Main Blank Content Screen */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 text-center z-10">
        <div className="max-w-md w-full py-12 px-8 rounded-3xl bg-slate-900/30 border border-slate-800/50 backdrop-blur-xl shadow-2xl">
          
          {/* Subtle Bank-App Watermark */}
          <div className="w-16 h-16 bg-slate-900/80 border border-slate-850 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-inner">
            <Landmark className="w-8 h-8 text-slate-500/80" />
          </div>
 
          <h2 className="text-2xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-slate-200 to-slate-400">
            IDBI GENERIC APP
          </h2>
          
          <p className="text-sm text-slate-400 mt-3 font-medium leading-relaxed">
            Welcome to the IDBI Mobile Banking platform. Open the menu at the top-left to navigate core bank services and wealth advisory features.
          </p>
 
          <div className="mt-8 flex flex-col gap-3 justify-center items-center">
            <button
              onClick={() => setDrawerOpen(true)}
              className="px-5 py-2.5 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/60 rounded-xl text-xs font-semibold text-slate-300 hover:text-slate-100 transition-all flex items-center gap-2"
            >
              <Menu className="w-3.5 h-3.5" />
              Open Navigation Menu
            </button>
          </div>
        </div>
      </main>
 
      {/* Slide-over Left Drawer */}
      <div 
        className={`fixed inset-0 z-50 transition-opacity duration-300 ${
          drawerOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      >
        {/* Drawer Backdrop overlay */}
        <div 
          onClick={() => setDrawerOpen(false)}
          className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
        />
 
        {/* Drawer Content */}
        <div 
          className={`absolute top-0 bottom-0 left-0 w-80 bg-slate-900 border-r border-slate-855 p-6 flex flex-col justify-between shadow-2xl transition-transform duration-350 ease-out transform ${
            drawerOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div>
            {/* Drawer Header with Close Button */}
            <div className="flex items-center justify-between pb-6 border-b border-slate-800/80">
              <div className="flex items-center gap-2">
                <Landmark className="w-5 h-5 text-primary" />
                <span className="font-bold text-sm tracking-tight text-slate-200">IDBI NetBanking</span>
              </div>
              <button 
                onClick={() => setDrawerOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
 
            {/* Profile Brief */}
            <div className="mt-5 p-3.5 bg-slate-950/50 border border-slate-855 rounded-2xl flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                <User className="w-4 h-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-xs font-bold text-slate-200 truncate">{profile.name}</h4>
                <p className="text-[10px] text-slate-400 truncate">{profile.occupation}</p>
              </div>
            </div>
 
            {/* Menu Options */}
            <nav className="mt-8 flex flex-col gap-2">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1 px-1">
                Banking Services
              </div>
 
              {/* IDBI Existing Option 1 */}
              <div className="flex items-center justify-between p-3 rounded-xl border border-slate-855 hover:border-slate-800 bg-slate-950/20 text-slate-400 cursor-not-allowed select-none">
                <div className="flex items-center gap-3">
                  <CreditCard className="w-4.5 h-4.5 text-slate-600" />
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold">Account Details</span>
                    <span className="text-[8px] text-slate-500">IDBI existing option</span>
                  </div>
                </div>
              </div>
 
              {/* IDBI Existing Option 2 */}
              <div className="flex items-center justify-between p-3 rounded-xl border border-slate-855 hover:border-slate-800 bg-slate-950/20 text-slate-400 cursor-not-allowed select-none">
                <div className="flex items-center gap-3">
                  <Send className="w-4.5 h-4.5 text-slate-600" />
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold">Fund Transfer</span>
                    <span className="text-[8px] text-slate-500">IDBI existing option</span>
                  </div>
                </div>
              </div>
 
              {/* IDBI Existing Option 3 */}
              <div className="flex items-center justify-between p-3 rounded-xl border border-slate-855 hover:border-slate-800 bg-slate-950/20 text-slate-400 cursor-not-allowed select-none">
                <div className="flex items-center gap-3">
                  <Landmark className="w-4.5 h-4.5 text-slate-600" />
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold">Bill Payments</span>
                    <span className="text-[8px] text-slate-500">IDBI existing option</span>
                  </div>
                </div>
              </div>
 
              {/* Space divider */}
              <div className="h-px bg-slate-855 my-3" />
 
              <div className="text-[10px] font-bold text-primary uppercase tracking-wider mb-1 px-1">
                Advisory Services
              </div>
 
              {/* Custom option: Wealth Insight */}
              <button 
                onClick={handleWealthInsightClick}
                className="flex items-center justify-between p-3.5 rounded-2xl bg-primary hover:bg-primary/90 border border-primary text-white cursor-pointer active:scale-[0.98] transition-all duration-200 shadow-lg shadow-primary/20 group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-white/20 border border-white/20">
                    <TrendingUp className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-xs font-bold text-white">Wealth Insight</span>
                    <span className="text-[8px] text-white/80 font-semibold tracking-wider uppercase mt-0.5">AI Advisory Engine</span>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-white group-hover:translate-x-1 transition-transform" />
              </button>
            </nav>
          </div>
 
          {/* Drawer Footer / Exit */}
          <div className="flex flex-col gap-2">
            <button
              onClick={() => {
                setDrawerOpen(false)
                navigate('/')
              }}
              className="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl border border-slate-800 hover:bg-slate-800/40 text-xs font-semibold text-slate-400 hover:text-slate-300 transition-colors"
            >
              Change Profile
            </button>
            
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl hover:bg-red-950/20 hover:text-red-400 text-xs font-semibold text-slate-500 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
