import { useState, useEffect, useRef } from 'react'
import { createSession, sendMessage, getSession } from './api.js'

/* ── Helpers ──────────────────────────────────────────── */
function fmt(ts) {
  return new Date(ts).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function isAppointmentConfirm(msg) {
  if (msg.state !== 'done') return false
  const t = msg.content.toLowerCase()
  return t.includes('appointment') || t.includes('confirmed') || t.includes('booked') || t.includes('slot')
}

/* ── Emergency doctor card ────────────────────────────── */
function EmergencyDoctorCard({ doctor, onBook }) {
  if (!doctor) return null
  const telHref = `tel:${doctor.phone.replace(/[^0-9]/g, '')}`
  return (
    <div style={{
      border: '1.5px solid #cc0000',
      background: '#fff0f0',
      borderRadius: 12,
      padding: '14px 16px',
      maxWidth: '78%',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
    }}>
      <div>
        <div style={{ fontWeight: 700, fontSize: 13, color: '#cc0000', marginBottom: 4 }}>
          ⚠️  Emergency Contact
        </div>
        <div style={{ fontWeight: 700, fontSize: 15, color: '#1a1a1a' }}>{doctor.name}</div>
        <div style={{ fontSize: 13, color: '#555' }}>{doctor.department}</div>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <a
          href={telHref}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: '#cc0000', color: '#fff',
            borderRadius: 20, padding: '7px 14px',
            fontSize: 13, fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          📞 Call Now: {doctor.phone}
        </a>
        <button
          onClick={onBook}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: '#fff', color: '#cc0000',
            border: '1.5px solid #cc0000',
            borderRadius: 20, padding: '7px 14px',
            fontSize: 13, fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          🏥 Book Emergency Slot
        </button>
      </div>
    </div>
  )
}

/* ── Sub-components ───────────────────────────────────── */
function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2 }}>
      <span style={{ fontSize: 11, color: '#666', fontWeight: 600, marginRight: 4 }}>Medibot</span>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 5,
        background: '#f0f0f0', borderRadius: '18px 18px 18px 4px',
        padding: '10px 14px',
      }}>
        {[0, 1, 2].map(i => (
          <span key={i} className="typing-dot" style={{ animationDelay: `${i * 0.2}s` }} />
        ))}
      </div>
    </div>
  )
}

function Bubble({ msg, showLabel }) {
  const isUser = msg.role === 'user'

  let bubbleStyle = {
    padding: '10px 14px',
    borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
    maxWidth: '78%',
    fontSize: 14,
    lineHeight: 1.55,
    wordBreak: 'break-word',
    whiteSpace: 'pre-wrap',
  }

  let prefix = ''

  if (isUser) {
    bubbleStyle = { ...bubbleStyle, background: '#0066CC', color: '#fff', alignSelf: 'flex-end' }
  } else if (msg.is_emergency) {
    bubbleStyle = {
      ...bubbleStyle,
      background: '#fff0f0',
      borderLeft: '4px solid #ef4444',
      color: '#1a1a1a',
      fontWeight: 600,
    }
    prefix = '⚠️ '
  } else if (isAppointmentConfirm(msg)) {
    bubbleStyle = {
      ...bubbleStyle,
      background: '#f0fff4',
      borderLeft: '4px solid #22c55e',
      color: '#1a1a1a',
    }
    prefix = '✅ '
  } else {
    bubbleStyle = { ...bubbleStyle, background: '#f0f0f0', color: '#1a1a1a' }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start', gap: 2 }}>
      {!isUser && showLabel && (
        <span style={{ fontSize: 11, color: '#666', fontWeight: 600, marginLeft: 4 }}>Medibot</span>
      )}
      <div style={bubbleStyle}>{prefix}{msg.content}</div>
      <span style={{ fontSize: 10, color: '#bbb', marginTop: 1, marginLeft: isUser ? 0 : 4 }}>
        {fmt(msg.timestamp)}
      </span>
    </div>
  )
}

/* ── Main component ───────────────────────────────────── */
export default function ChatWindow({ onClose, onBotMessage }) {
  const [messages, setMessages]       = useState([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [token, setToken]             = useState(null)
  const [quickReplies, setQuickReplies] = useState([])
  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)

  /* Core send function — token passed explicitly to avoid stale closure */
  async function callSend(tkn, text) {
    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: new Date() }])
    setLoading(true)
    setQuickReplies([])
    try {
      const res = await sendMessage(tkn, text)
      const botMsg = {
        role: 'assistant',
        content: res.message,
        timestamp: new Date(),
        is_emergency: res.is_emergency,
        state: res.state,
        emergency_doctor: res.emergency_doctor || null,
      }
      setMessages(prev => [...prev, botMsg])
      setQuickReplies(res.quick_replies || [])
      if (onBotMessage) onBotMessage()
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  /* Init: get or create session, load history or auto-start */
  useEffect(() => {
    let alive = true
    ;(async () => {
      const isNew = !localStorage.getItem('kauvery_session')
      const tkn = await createSession()
      if (!alive) return
      setToken(tkn)

      if (isNew) {
        /* Fresh session — auto-greet */
        await callSend(tkn, 'hi')
      } else {
        /* Returning session — restore history */
        try {
          const session = await getSession(tkn)
          if (!alive) return
          const restored = (session.messages || []).map(m => ({
            role: m.role,
            content: m.content,
            timestamp: m.created_at ? new Date(m.created_at) : new Date(),
            state: session.state,
          }))
          if (restored.length > 0) {
            setMessages(restored)
          } else {
            await callSend(tkn, 'hi')
          }
        } catch {
          await callSend(tkn, 'hi')
        }
      }
    })()
    return () => { alive = false }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  /* Auto-scroll */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  /* User send */
  function handleSend() {
    const text = input.trim()
    if (!text || !token || loading) return
    setInput('')
    callSend(token, text)
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  return (
    <div className="chat-window">

      {/* Header */}
      <div style={{
        background: '#0066CC',
        padding: '14px 16px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0,
      }}>
        <div>
          <div style={{ color: '#fff', fontWeight: 700, fontSize: 16 }}>Medibot</div>
          <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: 11 }}>Kauvery Hospital · AI Assistant</div>
        </div>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: 20, padding: '4px 8px', borderRadius: 8, lineHeight: 1 }}
          aria-label="Close chat"
        >✕</button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 14px 4px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {messages.map((msg, i) => {
          const prev = messages[i - 1]
          const showLabel = msg.role === 'assistant' && (!prev || prev.role !== 'assistant')
          return (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <Bubble msg={msg} showLabel={showLabel} />
              {msg.is_emergency && msg.emergency_doctor && (
                <EmergencyDoctorCard
                  doctor={msg.emergency_doctor}
                  onBook={() => { if (token && !loading) callSend(token, 'book emergency appointment') }}
                />
              )}
            </div>
          )
        })}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} style={{ height: 4 }} />
      </div>

      {/* Quick replies */}
      {quickReplies.length > 0 && (
        <div style={{
          padding: '8px 12px',
          borderTop: '1px solid #eee',
          display: 'flex', gap: 8,
          overflowX: 'auto', flexShrink: 0,
        }}>
          {quickReplies.map(qr => (
            <button
              key={qr}
              className="quick-reply-btn"
              disabled={loading}
              onClick={() => { if (!loading && token) callSend(token, qr) }}
            >{qr}</button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ padding: '10px 12px', borderTop: '1px solid #eee', display: 'flex', gap: 8, flexShrink: 0 }}>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
          placeholder={loading ? 'Medibot is typing…' : 'Type a message…'}
          style={{
            flex: 1,
            border: '1.5px solid #dde3f0',
            borderRadius: 24,
            padding: '9px 16px',
            fontSize: 14,
            outline: 'none',
            background: loading ? '#f8f8f8' : '#fff',
            color: '#1a1a1a',
          }}
        />
        <button
          className="send-btn"
          disabled={loading || !input.trim() || !token}
          onClick={handleSend}
          aria-label="Send message"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  )
}
