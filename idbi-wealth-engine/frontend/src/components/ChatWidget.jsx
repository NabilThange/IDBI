import { useState, useEffect, useRef, useCallback } from 'react'
import { useSession } from '../context/SessionContext'
import { Orb } from './ui/orb'
import {
  Chat as MessageSquare, Trash as Trash2, CornersOut as Maximize2, CornersIn as Minimize2,
  Waveform as AudioLines, ArrowRight, CaretDown as ChevronDown, X, DotsSix as GripHorizontal
} from '@phosphor-icons/react'
import apiClient from '@/lib/apiClient'
import ReactMarkdown from 'react-markdown'

// ─── Language helpers ────────────────────────────────────────────────────────

const LANGUAGE_CODES = {
  English: 'en-IN',
  Hindi:   'hi-IN',
  Marathi: 'mr-IN',
  Tamil:   'ta-IN',
  Telugu:  'te-IN',
  Bengali: 'bn-IN',
  Gujarati:'gu-IN',
  Kannada: 'kn-IN',
  Malayalam:'ml-IN',
  Punjabi: 'pa-IN',
  Odia:    'od-IN',
}

const getLanguageCode = (language) => LANGUAGE_CODES[language] || 'en-IN'

// ─── Component ───────────────────────────────────────────────────────────────

export default function ChatWidget() {
  const { profile, sessionId, isAuthenticated } = useSession()

  // ── UI state ──────────────────────────────────────────────────────────────
  const [chatOpen,      setChatOpen]      = useState(false)
  const [chatMaximized, setChatMaximized] = useState(false)
  const [chatMessage,   setChatMessage]   = useState('')
  const [chatHistory,   setChatHistory]   = useState([])
  const [chatLoading,   setChatLoading]   = useState(false)
  const [chatLanguage,  setChatLanguage]  = useState('English')

  // ── Drag state ────────────────────────────────────────────────────────────
  // Position of the widget anchor (bottom-right corner offsets from viewport)
  const [pos,       setPos]       = useState({ right: 24, bottom: 24 })
  const dragging    = useRef(false)
  const dragStart   = useRef({ x: 0, y: 0, right: 24, bottom: 24 })
  const widgetRef   = useRef(null)
  const hasDragged  = useRef(false)

  // ── Voice state machine ───────────────────────────────────────────────────
  // 'idle' | 'listening' | 'recording' | 'processing' | 'speaking'
  const [voiceState, setVoiceState] = useState('idle')
  const voiceStateRef    = useRef('idle')
  const greetingPlayedRef= useRef(false)
  const currentAudioRef  = useRef(null)
  const vadStreamRef     = useRef(null)
  const vadContextRef    = useRef(null)
  const vadRecorderRef   = useRef(null)
  const vadChunksRef     = useRef([])
  const vadActiveRef     = useRef(false)
  const isListeningRef   = useRef(false)
  const recognitionRef   = useRef(null)
  const retryCountRef    = useRef(0)

  // ── Scroll to bottom ──────────────────────────────────────────────────────
  const messagesEndRef = useRef(null)
  useEffect(() => {
    if (chatOpen) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory, chatOpen])

  // ── Sync language from profile ─────────────────────────────────────────────
  useEffect(() => {
    if (profile?.language_preference) setChatLanguage(profile.language_preference)
  }, [profile])

  // ── Reset language to profile default when chat opens ──────────────────────
  useEffect(() => {
    if (chatOpen && profile?.language_preference) {
      setChatLanguage(profile.language_preference)
    }
  }, [chatOpen, profile])

  // ── Fetch history when widget opens ───────────────────────────────────────
  useEffect(() => {
    if (chatOpen && sessionId) fetchChatHistory()
  }, [chatOpen, sessionId])

  // ── Clean up voice when auth changes ──────────────────────────────────────
  useEffect(() => {
    if (!isAuthenticated) stopVoiceSession()
  }, [isAuthenticated])

  // Don't render anything if not authenticated
  if (!isAuthenticated) return null

  // ─── Helpers ───────────────────────────────────────────────────────────────

  const setVoiceStateSynced = (s) => {
    voiceStateRef.current = s
    setVoiceState(s)
  }

  const fetchChatHistory = async () => {
    try {
      const response = await apiClient.get(`/api/chat/history?session_id=${sessionId}`)
      setChatHistory(response.data.messages || [])
    } catch (err) {
      console.error('Error fetching chat history:', err)
    }
  }

  // ─── Text chat ─────────────────────────────────────────────────────────────

  const sendChatMessage = async (e) => {
    if (e) e.preventDefault()
    if (!chatMessage.trim()) return

    const userMsg = chatMessage
    setChatMessage('')
    setChatHistory(prev => [...prev, { role: 'user', content: userMsg }])
    setChatLoading(true)
    try {
      const res = await apiClient.post('/api/chat', { 
        message: userMsg, 
        session_id: sessionId,
        language: chatLanguage
      })
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: res.data.message,
        sources: res.data.sources,      // NEW: source pills
        action: res.data.action         // NEW: CTA button
      }])
    } catch {
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Connection issue. Try again.' }])
    } finally {
      setChatLoading(false)
    }
  }

  const clearChat = async () => {
    try {
      await apiClient.delete(`/api/chat/history?session_id=${sessionId}`)
      setChatHistory([])
    } catch (err) {
      console.error(err)
    }
  }

  // ─── Voice session ─────────────────────────────────────────────────────────

  const sendVoiceGreeting = async () => {
    greetingPlayedRef.current = true
    try {
      const lang   = chatLanguage || profile?.language_preference || 'English'
      const gender = profile?.gender === 'Female' ? 'Female' : 'Male'
      const formData = new FormData()
      formData.append('session_id',    sessionId)
      formData.append('language_code', getLanguageCode(lang))
      formData.append('speaker_gender',gender)

      const response = await apiClient.post('/api/voice/greet', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const { greeting_text, audio } = response.data
      setChatHistory(prev => [
        ...prev.filter(m => m._isGreeting !== true),
        { role: 'assistant', content: greeting_text, _isGreeting: true }
      ])
      if (audio) await playAudioAndWait(audio)
    } catch (err) {
      console.error('[GREET] Failed:', err?.response?.data || err.message)
    }
  }

  const startVoiceSession = async () => {
    if (voiceStateRef.current !== 'idle') return
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      alert('Microphone access denied. Please allow microphone access.')
      return
    }
    vadStreamRef.current = stream
    setVoiceStateSynced('listening')
    if (!greetingPlayedRef.current) {
      setVoiceStateSynced('speaking')
      await sendVoiceGreeting()
    }
    setVoiceStateSynced('listening')
    startVADLoop(stream)
  }

  const stopVoiceSession = () => {
    vadActiveRef.current = false
    setVoiceStateSynced('idle')
    if (currentAudioRef.current) { currentAudioRef.current.pause(); currentAudioRef.current = null }
    if (vadRecorderRef.current && vadRecorderRef.current.state !== 'inactive') {
      try { vadRecorderRef.current.stop() } catch (_) {}
    }
    if (vadContextRef.current) { vadContextRef.current.close().catch(() => {}); vadContextRef.current = null }
    if (vadStreamRef.current) { vadStreamRef.current.getTracks().forEach(t => t.stop()); vadStreamRef.current = null }
  }

  const startVADLoop = (stream) => {
    const audioCtx = new AudioContext()
    vadContextRef.current = audioCtx
    const analyser = audioCtx.createAnalyser()
    analyser.fftSize = 512
    const source = audioCtx.createMediaStreamSource(stream)
    source.connect(analyser)
    const dataArray = new Uint8Array(analyser.frequencyBinCount)

    const SPEECH_THRESHOLD = 18
    const FRAMES_TO_START  = 4
    const FRAMES_TO_STOP   = 50

    let speechFrames = 0, silenceFrames = 0, isCapturing = false
    vadActiveRef.current = true

    const tick = () => {
      if (!vadActiveRef.current) return
      analyser.getByteFrequencyData(dataArray)
      const energy   = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
      const isSpeech = energy > SPEECH_THRESHOLD

      if (isSpeech) {
        speechFrames++; silenceFrames = 0
        if (currentAudioRef.current) {
          currentAudioRef.current.pause(); currentAudioRef.current = null
          setVoiceStateSynced('listening')
        }
        if (!isCapturing && speechFrames >= FRAMES_TO_START && voiceStateRef.current === 'listening') {
          isCapturing = true; vadChunksRef.current = []
          const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
          vadRecorderRef.current = recorder
          recorder.ondataavailable = e => { if (e.data.size > 0) vadChunksRef.current.push(e.data) }
          recorder.onstop = async () => {
            if (!vadActiveRef.current) return
            const blob = new Blob(vadChunksRef.current, { type: 'audio/webm' })
            setVoiceStateSynced('processing')
            await sendVoiceMessage(blob)
            if (vadActiveRef.current) setVoiceStateSynced('listening')
          }
          recorder.start(); setVoiceStateSynced('recording')
        }
      } else {
        silenceFrames++; speechFrames = 0
        if (isCapturing && silenceFrames >= FRAMES_TO_STOP) {
          isCapturing = false; silenceFrames = 0
          if (vadRecorderRef.current && vadRecorderRef.current.state === 'recording') {
            vadRecorderRef.current.stop()
          }
        }
      }
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }

  const sendVoiceMessage = async (audioBlob) => {
    setChatLoading(true)
    try {
      const lang = chatLanguage || profile?.language_preference || 'English'
      const formData = new FormData()
      formData.append('audio',          audioBlob, 'recording.webm')
      formData.append('session_id',     sessionId)
      formData.append('language_code',  getLanguageCode(lang))
      formData.append('speaker_gender', profile?.gender === 'Female' ? 'Female' : 'Male')

      const response = await apiClient.post('/api/voice/converse', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const { native_question, native_answer, audio } = response.data
      setChatHistory(prev => [...prev,
        { role: 'user',      content: native_question },
        { role: 'assistant', content: native_answer   }
      ])
      if (audio && vadActiveRef.current) {
        setVoiceStateSynced('speaking')
        await playAudioAndWait(audio)
        if (vadActiveRef.current) setVoiceStateSynced('listening')
      }
    } catch (error) {
      console.error('[VOICE] Error:', error)
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }])
    } finally {
      setChatLoading(false)
    }
  }

  const playAudioAndWait = (base64Audio) => new Promise((resolve) => {
    try {
      const raw = Array.isArray(base64Audio) ? base64Audio[0] : base64Audio
      if (!raw || typeof raw !== 'string') { resolve(); return }
      const byteCharacters = atob(raw)
      const byteArray = new Uint8Array(byteCharacters.length)
      for (let i = 0; i < byteCharacters.length; i++) byteArray[i] = byteCharacters.charCodeAt(i)
      const audioBlob = new Blob([byteArray], { type: 'audio/wav' })
      const audioUrl  = URL.createObjectURL(audioBlob)
      const audio     = new Audio(audioUrl)
      currentAudioRef.current = audio
      const cleanup = () => {
        URL.revokeObjectURL(audioUrl)
        if (currentAudioRef.current === audio) currentAudioRef.current = null
        resolve()
      }
      audio.onended = cleanup; audio.onerror = cleanup
      audio.play().catch(err => { console.error('[AUDIO] play() failed:', err.message); cleanup() })
    } catch (e) {
      console.error('[AUDIO] setup error:', e); resolve()
    }
  })

  const handleActionButtonClick = async () => {
    if (chatMessage.trim()) {
      sendChatMessage()
    } else if (voiceStateRef.current !== 'idle') {
      stopVoiceSession()
    } else {
      await startVoiceSession()
    }
  }

  // ─── Drag logic ────────────────────────────────────────────────────────────

  const onDragStart = (e) => {
    // Prevent drag on maximize/minimize/close buttons in header (they are not the currentTarget, which is header div or FAB button)
    if (e.target.closest('button') && e.currentTarget !== e.target.closest('button')) return
    
    // We don't want touch movements to trigger page scrolling while dragging the widget
    if (e.cancelable) e.preventDefault()
    
    dragging.current = true
    hasDragged.current = false
    const clientX = e.touches ? e.touches[0].clientX : e.clientX
    const clientY = e.touches ? e.touches[0].clientY : e.clientY
    dragStart.current = { x: clientX, y: clientY, right: pos.right, bottom: pos.bottom }

    const onMove = (ev) => {
      if (!dragging.current) return
      const cx = ev.touches ? ev.touches[0].clientX : ev.clientX
      const cy = ev.touches ? ev.touches[0].clientY : ev.clientY
      const dx = cx - dragStart.current.x
      const dy = cy - dragStart.current.y
      
      if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
        hasDragged.current = true
      }
      
      setPos({
        right:  Math.max(8, dragStart.current.right  - dx),
        bottom: Math.max(8, dragStart.current.bottom - dy),
      })
    }
    const onUp = () => {
      dragging.current = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup',   onUp)
      window.removeEventListener('touchmove', onMove)
      window.removeEventListener('touchend',  onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',   onUp)
    window.addEventListener('touchmove', onMove, { passive: false })
    window.addEventListener('touchend',  onUp)
  }

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div
      ref={widgetRef}
      className="fixed z-50 flex flex-col items-end"
      style={{ right: pos.right, bottom: pos.bottom }}
    >
      {/* Chat panel */}
      {chatOpen && (
        <div
          className={`bg-card text-card-foreground border border-border rounded-3xl shadow-2xl flex flex-col overflow-hidden mb-3 animate-slide-in transition-all duration-300 ${
            chatMaximized
              ? 'chat-maximized w-[calc(100vw-1.5rem)] md:w-[70vw] lg:w-[50vw] h-[80vh] md:h-[75vh]'
              : 'w-80 md:w-96 h-96'
          }`}
        >
          {/* Header — drag handle */}
          <div
            className="bg-emerald-600 px-4 py-3 text-white flex justify-between items-center cursor-grab active:cursor-grabbing select-none"
            onMouseDown={onDragStart}
            onTouchStart={onDragStart}
          >
            <div className="flex-1 flex items-center gap-2">
              <GripHorizontal className="w-3.5 h-3.5 text-emerald-300 shrink-0" />
              <div className="flex-1">
                <h4 className="font-bold text-xs mb-1">IDBI Wealth AI Assistant</h4>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-emerald-100 font-medium">
                    Default: {profile?.language_preference || 'English'}
                  </span>
                  <span className="text-emerald-200">•</span>
                  <div className="relative">
                    <select
                      value={chatLanguage}
                      onChange={(e) => setChatLanguage(e.target.value)}
                      className="text-[10px] bg-emerald-700 text-white font-medium border border-emerald-500 rounded px-2 py-0.5 pr-6 appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-white"
                      onMouseDown={(e) => e.stopPropagation()}
                    >
                      {Object.keys(LANGUAGE_CODES).map(lang => (
                        <option key={lang} value={lang}>{lang}</option>
                      ))}
                    </select>
                    <ChevronDown className="w-3 h-3 absolute right-1 top-1/2 -translate-y-1/2 pointer-events-none" />
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onMouseDown={(e) => e.stopPropagation()}
                onTouchStart={(e) => e.stopPropagation()}
                onClick={() => setChatMaximized(!chatMaximized)}
                className="text-emerald-100 hover:text-white p-1 rounded-lg hover:bg-white/10 flex items-center justify-center"
                title={chatMaximized ? 'Minimize window' : 'Maximize window'}
              >
                {chatMaximized ? <Minimize2 color="white" className="w-4 h-4" /> : <Maximize2 color="white" className="w-4 h-4" />}
              </button>
              <button
                onMouseDown={(e) => e.stopPropagation()}
                onTouchStart={(e) => e.stopPropagation()}
                onClick={clearChat}
                className="text-emerald-100 hover:text-white p-1 rounded-lg hover:bg-white/10 flex items-center justify-center"
                title="Clear conversation"
              >
                <Trash2 color="white" className="w-4 h-4" />
              </button>
              <button
                onMouseDown={(e) => e.stopPropagation()}
                onTouchStart={(e) => e.stopPropagation()}
                onClick={() => { setChatOpen(false); setChatMaximized(false) }}
                className="text-emerald-100 hover:text-white p-1 rounded-lg hover:bg-white/10 flex items-center justify-center"
                title="Close"
              >
                <X color="white" className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div
            className="flex-1 overflow-y-auto flex flex-col gap-3 font-sans relative p-4 bg-background"
          >
            {/* Voice Orb overlay */}
            {voiceState !== 'idle' && (
              <div
                className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-background"
              >
                <div className="relative h-40 w-40">
                  <div className="absolute inset-0 rounded-full bg-emerald-50 shadow-[inset_0_2px_8px_rgba(0,0,0,0.08)]" />
                  <div className="absolute inset-1 rounded-full overflow-hidden bg-white shadow-[inset_0_0_12px_rgba(0,0,0,0.04)]">
                    <Orb
                      colors={[
                        voiceState === 'speaking'   ? '#008a50' :
                        voiceState === 'recording'  ? '#ca3214' :
                        voiceState === 'processing' ? '#f59e0b' :
                        '#72e3ad',
                        '#008a50'
                      ]}
                      seed={1234}
                      agentState={
                        voiceState === 'speaking'   ? 'speaking'  :
                        voiceState === 'recording'  ? 'listening' :
                        voiceState === 'processing' ? 'thinking'  :
                        'listening'
                      }
                      volumeMode="auto"
                    />
                  </div>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className={`text-xs font-semibold animate-pulse ${
                    voiceState === 'speaking'   ? 'text-primary' :
                    voiceState === 'recording'  ? 'text-destructive'   :
                    voiceState === 'processing' ? 'text-amber-600'  :
                    'text-primary'
                  }`}>
                    {voiceState === 'speaking'   ? 'AI Speaking…'        :
                     voiceState === 'recording'  ? 'Listening…'          :
                     voiceState === 'processing' ? 'Processing…'         :
                     'Ready — speak anytime'}
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {chatLanguage || profile?.language_preference || 'English'} • tap wave to end
                  </span>
                </div>
              </div>
            )}

            {chatHistory.length === 0 && voiceState === 'idle' ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-muted-foreground text-sm">Start a conversation...</p>
              </div>
            ) : (
              chatHistory.map((msg, idx) => (
                <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div
                    className={`max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm shadow-sm ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground rounded-br-sm'
                        : 'bg-card text-card-foreground rounded-bl-sm border border-border'
                    }`}
                  >
                    {msg.role === 'user' ? (
                      msg.content
                    ) : (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}
                  </div>

                  {/* Source Citations */}
                  {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                    <div className="flex gap-1.5 flex-wrap mt-2 max-w-[80%]">
                      {msg.sources.map((src, i) => (
                        <a
                          key={i}
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded border border-border transition-colors"
                        >
                          📄 {src.title.length > 35 ? src.title.substring(0, 35) + '...' : src.title}
                        </a>
                      ))}
                    </div>
                  )}

                  {/* CTA Button (only for assistant with action) */}
                  {msg.role === 'assistant' && msg.action && (
                    <button 
                      onClick={() => window.open(msg.action.url, '_blank', 'noopener,noreferrer')}
                      className="mt-2 max-w-[80%] w-full px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-semibold rounded-lg shadow-md transition-all"
                    >
                      {msg.action.label} →
                    </button>
                  )}
                </div>
              ))
            )}

            {chatLoading && (
              <div className="flex justify-start">
                <div
                  className="bg-card text-card-foreground max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm shadow-sm rounded-bl-sm border border-border flex items-center gap-2"
                >
                  <span className="w-2 h-2 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="px-3 py-3 border-t border-border bg-card">
            <form
              onSubmit={(e) => { e.preventDefault(); handleActionButtonClick() }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                placeholder="Ask a question..."
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                className="flex-1 bg-muted text-foreground border border-border rounded-full px-4 py-2 text-xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
              <button
                type="button"
                onClick={handleActionButtonClick}
                disabled={chatLoading && voiceState === 'idle'}
                className={`p-2.5 rounded-full flex items-center justify-center transition-all shadow-md ${
                  chatMessage.trim()
                    ? 'bg-primary hover:bg-primary/90 text-primary-foreground shadow-primary/20'
                    : voiceState !== 'idle'
                    ? 'bg-destructive hover:bg-destructive/90 text-destructive-foreground shadow-destructive/20 animate-pulse'
                    : 'bg-primary hover:bg-primary/90 text-primary-foreground shadow-primary/20'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
                title={chatMessage.trim() ? 'Send message' : voiceState !== 'idle' ? 'End voice session' : 'Start voice session'}
              >
                {chatMessage.trim() ? (
                  <ArrowRight className="w-5 h-5" />
                ) : (
                  <AudioLines className="w-5 h-5" />
                )}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* FAB toggle button */}
      <button
        onMouseDown={onDragStart}
        onTouchStart={onDragStart}
        onClick={(e) => {
          if (hasDragged.current) {
            e.preventDefault()
            return
          }
          if (chatOpen) setChatMaximized(false)
          setChatOpen(!chatOpen)
        }}
        className="bg-primary hover:bg-primary/90 text-primary-foreground p-4 rounded-full shadow-2xl flex items-center justify-center transition-all duration-300 transform hover:scale-105 cursor-grab active:cursor-grabbing"
        title="Chat with IDBI Wealth AI"
      >
        <MessageSquare className="w-6 h-6" />
      </button>
    </div>
  )
}
