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

/* ── Message text renderer ────────────────────────────── */
const DISCLAIMER_RE = /⚠️DISCLAIMER:([\s\S]*?)⚠️END/g

function renderLines(text, keyOffset = 0) {
  return text.split('\n').map((line, i) => {
    if (line.startsWith('💊') || line.startsWith('🏠'))
      return <div key={keyOffset + i} style={{ fontWeight: 'bold', fontSize: '0.95rem', marginTop: '10px' }}>{line}</div>
    if (line.startsWith('•'))
      return <div key={keyOffset + i} style={{ paddingLeft: '16px', margin: '2px 0' }}>{line}</div>
    if (line.toLowerCase().includes('appointment reference number'))
      return <div key={keyOffset + i} style={{ fontWeight: 'bold', fontSize: '1rem', marginTop: '8px', color: '#0066CC' }}>{line}</div>
    if (line.trim() === '')
      return <div key={keyOffset + i} style={{ height: '6px' }} />
    return <div key={keyOffset + i}>{line}</div>
  })
}

function renderMessageText(text) {
  const parts = []
  let last = 0
  let match
  let idx = 0
  DISCLAIMER_RE.lastIndex = 0
  while ((match = DISCLAIMER_RE.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(...renderLines(text.slice(last, match.index), idx))
      idx += 100
    }
    parts.push(
      <div key={`disc-${idx}`} style={{
        background: '#fffbea',
        borderLeft: '3px solid #f59e0b',
        fontSize: '0.85rem',
        fontStyle: 'italic',
        padding: '8px 12px',
        borderRadius: '4px',
        margin: '6px 0',
      }}>
        {match[1].trim()}
      </div>
    )
    idx += 1
    last = match.index + match[0].length
  }
  if (last < text.length) {
    parts.push(...renderLines(text.slice(last), idx))
  }
  return parts
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
    whiteSpace: isUser ? 'pre-wrap' : 'normal',
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
      <div style={bubbleStyle}>
        {isUser ? `${prefix}${msg.content}` : <>{prefix}{renderMessageText(msg.content)}</>}
      </div>
      <span style={{ fontSize: 10, color: '#bbb', marginTop: 1, marginLeft: isUser ? 0 : 4 }}>
        {fmt(msg.timestamp)}
      </span>
    </div>
  )
}

/* ── Main component ───────────────────────────────────── */
export default function ChatWindow({ onClose, onBotMessage }) {
  const [messages, setMessages]         = useState([])
  const [input, setInput]               = useState('')
  const [loading, setLoading]           = useState(false)
  const [token, setToken]               = useState(null)
  const [quickReplies, setQuickReplies] = useState([])
  const [qrClickCount, setQrClickCount] = useState(0)   // tracks clicks per turn
  const [sessionKey, setSessionKey]     = useState(0)   // bumped by Start Over to re-run init
  const isSendingRef      = useRef(false)               // synchronous in-flight guard
  const userClickedReply  = useRef(false)               // true after any QR click until state changes
  const prevStateRef      = useRef(null)                // last known conversation state
  const bottomRef         = useRef(null)
  const inputRef          = useRef(null)

  /* Core send function — token passed explicitly to avoid stale closure */
  async function callSend(tkn, text) {
    if (isSendingRef.current) return              // behaviour 2: ignore if already in flight
    isSendingRef.current = true
    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: new Date() }])
    setLoading(true)
    setQuickReplies([])                           // behaviour 1: buttons gone immediately
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
      // BUG 1 fix: suppress new quick replies if user already clicked one this turn,
      // unless the state just changed (new stage = new set of buttons is appropriate)
      if (userClickedReply.current) {
        if (res.state !== prevStateRef.current) {
          userClickedReply.current = false          // state changed — reset flag, show new buttons
          setQuickReplies(res.quick_replies || [])
        } else {
          setQuickReplies([])                       // same state — keep buttons gone
        }
      } else {
        setQuickReplies(res.quick_replies || [])
      }
      prevStateRef.current = res.state
      setQrClickCount(0)                          // reset click counter for the new turn
      if (onBotMessage) onBotMessage()
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
      isSendingRef.current = false
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  /* Quick reply click handler — all guard logic lives here */
  function handleQuickReply(qr) {
    if (isSendingRef.current) return              // behaviour 2: in-flight, ignore silently

    const newCount = qrClickCount + 1
    setQrClickCount(newCount)

    if (newCount >= 2) {                          // behaviour 3: 2nd click in same turn
      setQuickReplies([])
      setMessages(prev => [...prev, {
        role: 'system',
        content: 'Please type your response or wait for Medibot to reply.',
        timestamp: new Date(),
      }])
      return
    }

    userClickedReply.current = true               // mark: suppress re-showing buttons on response
    callSend(token, qr)                           // behaviour 1: first click sends + clears
  }

  /* Start Over — behaviour 4 */
  function handleStartOver() {
    localStorage.removeItem('kauvery_session')
    isSendingRef.current = false
    userClickedReply.current = false
    prevStateRef.current = null
    setMessages([])
    setQuickReplies([])
    setQrClickCount(0)
    setInput('')
    setLoading(false)
    setToken(null)
    setSessionKey(k => k + 1)                     // re-triggers init useEffect
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
        await callSend(tkn, 'hi')
      } else {
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
  }, [sessionKey]) // eslint-disable-line react-hooks/exhaustive-deps

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
          if (msg.role === 'system') {
            return <div key={i} className="system-msg">{msg.content}</div>
          }
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
          {quickReplies.map(qr => {
            const isEmergency = qr.startsWith('🚨')
            const isSafe      = qr.startsWith('✅')
            return (
              <button
                key={qr}
                className="quick-reply-btn"
                disabled={loading}
                onClick={() => handleQuickReply(qr)}
                style={
                  isEmergency ? { background: '#dc2626', color: '#fff', borderColor: '#dc2626' } :
                  isSafe      ? { background: '#16a34a', color: '#fff', borderColor: '#16a34a' } :
                  undefined
                }
              >{qr}</button>
            )
          })}
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

      {/* Start over */}
      <button className="start-over-link" onClick={handleStartOver}>
        🔄 Start new conversation
      </button>
    </div>
  )
}
