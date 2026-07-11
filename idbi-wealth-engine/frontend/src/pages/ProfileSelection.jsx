import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../context/SessionContext'
import apiClient from '@/lib/apiClient'
import { User, TrendUp as TrendingUp } from '@phosphor-icons/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'

export default function ProfileSelection() {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { selectProfile, checkQuizStatus, isAuthenticated } = useSession()
  const navigate = useNavigate()

  // Disabled auto-redirect on mount to allow profile switching in demo mode
  // useEffect(() => {
  //   if (isAuthenticated) {
  //     navigate('/bank-app')
  //   }
  // }, [isAuthenticated, navigate])

  const fetchProfiles = async () => {
    setLoading(true)
    try {
      const response = await apiClient.get('/api/profiles')
      setProfiles(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load profiles')
      console.error('Error fetching profiles:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchProfiles()
    }, 0)
    return () => clearTimeout(timer)
  }, [])

  const handleSelectProfile = async (profileId) => {
    const success = await selectProfile(profileId)
    if (success) {
      navigate('/bank-app')
    }
  }

  const getRiskColor = (risk) => {
    const colors = {
      'Very Conservative': 'bg-green-500',
      'Conservative': 'bg-blue-500',
      'Moderate': 'bg-amber-500',
      'Aggressive': 'bg-red-500'
    }
    return colors[risk] || 'bg-purple-500'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
        <div className="w-12 h-12 border-4 border-primary/25 border-t-primary rounded-full animate-spin"></div>
        <p className="text-muted-foreground text-sm mt-4 font-medium font-sans">Loading advisor profiles...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center font-sans">
        <span className="text-destructive text-lg font-bold mb-2">Error Loading Profiles</span>
        <p className="text-muted-foreground text-sm max-w-xs">{error}</p>
        <button 
          onClick={fetchProfiles}
          className="mt-6 px-4 py-2 bg-primary hover:bg-primary/80 text-primary-foreground rounded-xl text-xs font-bold transition-all"
        >
          Retry Connection
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col justify-between p-6 select-none font-sans">
      
      {/* Top Header branding */}
      <div className="flex flex-col items-center text-center mt-2">
        <div className="bg-primary text-primary-foreground font-extrabold text-[9px] px-3.5 py-1 rounded-full tracking-wider uppercase mb-5 shadow-md">
          IDBI Wealth Advisor
        </div>
        
        <div className="w-14 h-14 bg-primary/10 rounded-2xl flex items-center justify-center shadow-lg mb-3">
          <TrendingUp className="w-7 h-7 text-primary" />
        </div>
        
        <h1 className="text-xl font-extrabold tracking-tight">IDBI Wealth Engine</h1>
        <p className="text-xs text-muted-foreground mt-1 max-w-[260px]">AI-Powered Personalized Wealth Advisory & Suitability Mapping</p>
      </div>

      {/* Main Selection Area */}
      <div className="my-auto py-2">
        <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider text-center mb-3">Select User Profile</h2>
        
        <div className="grid grid-cols-2 gap-3.5">
          {profiles.map((p) => {
            const risk = p.risk_profile?.risk_category || p.risk_profile || 'Moderate';
            return (
              <div 
                key={p.profile_id}
                onClick={() => handleSelectProfile(p.profile_id)}
                className="group relative bg-card border border-border hover:border-primary rounded-2xl p-4 flex flex-col items-center text-center cursor-pointer transition-all duration-200 transform active:scale-95"
              >
                {/* Visual Glow */}
                <div className="absolute inset-0 bg-primary/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity blur-md pointer-events-none"></div>
                
                {/* Avatar */}
                <div className="w-11 h-11 bg-background rounded-full flex items-center justify-center border border-border group-hover:border-primary/50 group-hover:bg-primary/10 transition-all mb-3.5">
                  <User className="w-5 h-5 text-muted-foreground group-hover:text-primary" />
                </div>
                
                <h3 className="text-xs font-bold truncate w-full">{p.name}</h3>
                <p className="text-[10px] text-muted-foreground mt-0.5 truncate w-full">{p.occupation}</p>
                <p className="text-[9px] text-slate-400 mt-1">{p.age} yrs | {p.city}</p>
                
                {/* Risk Category Badge */}
                <span className={`text-[8px] font-bold px-2 py-0.5 rounded-full mt-3 uppercase tracking-wider text-white ${getRiskColor(risk)}`}>
                  {risk.replace(' Conservative', ' Cons').replace('Very Cons', 'Cons')}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer info */}
      <div className="text-center mt-2">
        <p className="text-[9px] text-muted-foreground">Secure Connection Verified</p>
      </div>

    </div>
  )
}
