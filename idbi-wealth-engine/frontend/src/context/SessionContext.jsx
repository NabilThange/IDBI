import React, { createContext, useState, useContext, useEffect } from 'react'
import axios from 'axios'

const SessionContext = createContext()

export const useSession = () => {
  const context = useContext(SessionContext)
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider')
  }
  return context
}

export const SessionProvider = ({ children }) => {
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('sessionId') || null
  })
  const [profile, setProfile] = useState(() => {
    const saved = localStorage.getItem('profile')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (parsed && parsed.status === 'active' && parsed.profile) {
          return parsed.profile
        }
        return parsed
      } catch (e) {
        return null
      }
    }
    return null
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('sessionId', sessionId)
    } else {
      localStorage.removeItem('sessionId')
    }
  }, [sessionId])

  useEffect(() => {
    if (profile) {
      localStorage.setItem('profile', JSON.stringify(profile))
    } else {
      localStorage.removeItem('profile')
    }
  }, [profile])

  // Re-activate session with backend on page load.
  // The backend uses an in-memory session store that resets on server restart,
  // but the frontend keeps sessionId in localStorage. This effect re-registers
  // the session so API calls don't get 404 "No active session found".
  useEffect(() => {
    const reactivateSession = async () => {
      const storedSessionId = localStorage.getItem('sessionId')
      if (!storedSessionId) return

      try {
        // Try to get current session first — if it exists, we're good
        await axios.get(`/api/session/current/${storedSessionId}`)
      } catch (err) {
        if (err.response?.status === 404) {
          // Session lost (server restarted) — re-select the profile to restore it
          try {
            const response = await axios.post('/api/session/select', {
              profile_id: storedSessionId
            })
            const profileResponse = await axios.get(`/api/session/current/${response.data.session_id}`)
            setProfile(profileResponse.data.profile || profileResponse.data)
            setSessionId(response.data.session_id)
          } catch (reactivateErr) {
            // Profile no longer exists — clear stale session
            console.warn('Could not reactivate session, clearing:', reactivateErr)
            setSessionId(null)
            setProfile(null)
            localStorage.clear()
          }
        }
      }
    }

    reactivateSession()
  }, []) // run only on mount

  const selectProfile = async (profileId) => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.post('/api/session/select', {
        profile_id: profileId
      })
      
      setSessionId(response.data.session_id)
      
      const profileResponse = await axios.get(`/api/session/current/${response.data.session_id}`)
      setProfile(profileResponse.data.profile || profileResponse.data)
      
      return true
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to select profile')
      console.error('Profile selection error:', err)
      return false
    } finally {
      setLoading(false)
    }
  }

  const checkQuizStatus = async () => {
    if (!sessionId) return { quiz_completed: false, needs_refresh: true }
    
    try {
      const response = await axios.get('/api/quiz/status', {
        params: { session_id: sessionId }
      })
      return response.data
    } catch (err) {
      console.error('Error checking quiz status:', err)
      return { quiz_completed: false, needs_refresh: true }
    }
  }

  const clearSession = async () => {
    if (sessionId) {
      try {
        await axios.delete(`/api/session/${sessionId}`)
      } catch (err) {
        console.error('Error clearing session:', err)
      }
    }
    setSessionId(null)
    setProfile(null)
    localStorage.clear()
  }

  const value = {
    sessionId,
    profile,
    loading,
    error,
    selectProfile,
    clearSession,
    checkQuizStatus,
    isAuthenticated: !!sessionId && !!profile
  }

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  )
}
