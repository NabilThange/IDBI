import { useState, useEffect, useRef } from 'react'
import { useSession } from '../context/SessionContext'
import apiClient from '@/lib/apiClient'
import { PaperPlaneRight as Send, X, Chat as MessageSquare, Trash as Trash2, Question as HelpCircle, Wrench, Sparkle as Sparkles, Terminal } from '@phosphor-icons/react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import ReactMarkdown from 'react-markdown'

const QUICK_QUESTIONS = [
  "How's my financial health?",
  "Show me my spending patterns",
  "What products do you recommend?",
  "How are my goals progressing?"
]

export default function ChatBot({ isOpen, onClose }) {
  const { sessionId } = useSession()
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef(null)

  const fetchChatHistory = async () => {
    setLoading(true)
    try {
      const response = await apiClient.get(`/api/chat/history?session_id=${sessionId}`)
      setMessages(response.data.messages || [])
    } catch (err) {
      console.error('Error fetching chat history:', err)
    } finally {
      setLoading(false)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (isOpen && sessionId) {
      const timer = setTimeout(() => {
        fetchChatHistory()
      }, 0)
      return () => clearTimeout(timer)
    }
  }, [isOpen, sessionId])

  useEffect(() => {
    scrollToBottom()
  }, [messages, sending])

  const handleSend = async (textToSend) => {
    const text = textToSend || inputText
    if (!text.trim() || sending) return

    if (!textToSend) setInputText('')

    // Append user message locally
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setSending(true)

    try {
      const response = await apiClient.post('/api/chat', {
        message: text,
        session_id: sessionId
      })

      // Append assistant message
      setMessages(prev => [
        ...prev,
        { 
          role: 'assistant', 
          content: response.data.message,
          sources: response.data.sources,      // NEW: source pills
          action: response.data.action,        // NEW: CTA button
          toolCalls: response.data.tool_calls_made,
          iterations: response.data.iterations
        }
      ])

    } catch (err) {
      console.error('Error in chat:', err)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please verify your AI/ML API key and network connection.'
      }])
    } finally {
      setSending(false)
    }
  }

  const handleClearHistory = async () => {
    if (window.confirm('Are you sure you want to clear your conversation history?')) {
      try {
        await apiClient.delete(`/api/chat/history?session_id=${sessionId}`)
        setMessages([])
      } catch (err) {
        console.error('Error clearing chat history:', err)
      }
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-[450px] bg-card border-l shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="p-4 border-b bg-primary text-primary-foreground flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-sm leading-tight">AI Wealth Assistant</h3>
            <p className="text-[10px] text-primary-foreground/80 flex items-center gap-1">
              <Terminal className="w-2.5 h-2.5" /> Agentic Tool Calling & RAG
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleClearHistory}
              className="text-white hover:bg-white/10 h-8 w-8"
              title="Clear History"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="text-white hover:bg-white/10 h-8 w-8"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50 dark:bg-slate-900/5">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full gap-2">
            <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
            <p className="text-xs text-muted-foreground">Loading history...</p>
          </div>
        ) : messages.length === 0 ? (
          /* Welcome View */
          <div className="flex flex-col items-center justify-center py-10 px-4 text-center h-full space-y-6">
            <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center">
              <MessageSquare className="w-9 h-9 text-primary animate-pulse" />
            </div>
            <div>
              <h4 className="font-bold text-lg">IDBI AI wealth Assistant</h4>
              <p className="text-sm text-muted-foreground mt-2 max-w-[280px]">
                I can review your financial health, track goals, analyze expenses, and search IDBI products via RAG.
              </p>
            </div>
            
            <div className="w-full space-y-2 pt-4">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider text-left pl-1">
                Suggested Prompts
              </p>
              {QUICK_QUESTIONS.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(question)}
                  className="w-full text-left p-3 text-xs bg-card hover:bg-muted/50 border rounded-xl font-medium transition-all shadow-sm flex items-center justify-between group hover:border-primary/30"
                >
                  <span>{question}</span>
                  <HelpCircle className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Conversation history */
          <div className="space-y-4">
            {messages.map((msg, index) => {
              const isUser = msg.role === 'user'
              return (
                <div key={index} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <div className="max-w-[85%] flex flex-col">
                    <div
                      className={`p-3 rounded-2xl text-sm leading-relaxed ${
                        isUser
                          ? 'bg-primary text-primary-foreground rounded-tr-none shadow-md'
                          : 'bg-card text-foreground border rounded-tl-none shadow-sm'
                      }`}
                    >
                      {isUser ? (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      )}
                    </div>

                    {/* Source Citations */}
                    {!isUser && msg.sources && msg.sources.length > 0 && (
                      <div className="flex gap-2 flex-wrap mt-2">
                        {msg.sources.map((src, i) => (
                          <a
                            key={i}
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium bg-primary/10 hover:bg-primary/20 text-primary rounded border border-primary/20 transition-colors"
                          >
                            <span>📄 {src.title.length > 40 ? src.title.substring(0, 40) + '...' : src.title}</span>
                          </a>
                        ))}
                      </div>
                    )}

                    {/* CTA Button (only for assistant with action) */}
                    {!isUser && msg.action && (
                      <Button 
                        className="mt-3 w-full text-sm font-semibold shadow-md hover:shadow-lg transition-shadow" 
                        onClick={() => window.open(msg.action.url, '_blank', 'noopener,noreferrer')}
                      >
                        {msg.action.label} →
                      </Button>
                    )}

                    {/* Tool Calls Badge (only for assistant messages if present) */}
                    {!isUser && msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className="mt-1.5 flex flex-col gap-1 items-start">
                        <Badge 
                          variant="outline" 
                          className="bg-primary/5 dark:bg-primary/10 border-primary/20 dark:border-primary/30 text-[10px] py-0.5 px-2 flex items-center gap-1 font-semibold text-primary cursor-help"
                          title={`Completed in ${msg.iterations} agent loop iterations`}
                        >
                          <Wrench className="w-3 h-3 text-primary" />
                          Used {msg.toolCalls.length} tool{msg.toolCalls.length > 1 ? 's' : ''}
                        </Badge>
                        <div className="flex flex-wrap gap-1">
                          {msg.toolCalls.map((tc, idx) => (
                            <span 
                              key={idx} 
                              className="text-[9px] font-mono px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded border text-muted-foreground"
                            >
                              {tc.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
            
            {/* Real-time tools activity loader */}
            {sending && (
              <div className="flex justify-start">
                <div className="max-w-[85%] flex flex-col space-y-1.5">
                  {/* Visual typing indicator dots */}
                  <div className="bg-card text-foreground border rounded-2xl rounded-tl-none p-3 shadow-sm flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  
                  {/* Floating status updates */}
                  <span className="text-[10px] text-muted-foreground italic pl-1 flex items-center gap-1">
                    <Wrench className="w-3 h-3 animate-spin text-primary" /> Thinking & executing financial tools...
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="p-4 border-t bg-card">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex items-end gap-2"
        >
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your wealth, goals or loans..."
            className="flex-1 max-h-24 min-h-[40px] p-2.5 border rounded-xl text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary resize-none bg-slate-50/50"
            rows={1}
          />
          <Button
            type="submit"
            size="icon"
            disabled={!inputText.trim() || sending}
            className="h-10 w-10 rounded-xl bg-primary hover:bg-primary/90 flex-shrink-0 flex items-center justify-center text-white"
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}
