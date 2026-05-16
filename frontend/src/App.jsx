import { useState } from 'react'
import ChatWidget from './ChatWidget.jsx'
import ChatWindow from './ChatWindow.jsx'

const PRIMARY = '#0066CC'
const BG = '#f5f7fa'

export default function App() {
  const [chatOpen, setChatOpen] = useState(false)
  const [hasUnread, setHasUnread] = useState(false)

  const openChat = () => {
    setChatOpen(true)
    setHasUnread(false)
  }

  const handleNewBotMessage = () => {
    if (!chatOpen) setHasUnread(true)
  }

  return (
    <div style={{ background: BG, minHeight: '100vh', color: '#1a1a1a' }}>

      {/* ── Header ───────────────────────────────────────── */}
      <header style={{
        background: '#fff',
        borderBottom: '1px solid #e5e9f0',
        padding: '0 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 64,
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: PRIMARY,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ color: '#fff', fontWeight: 800, fontSize: 18 }}>K</span>
          </div>
          <span style={{ fontWeight: 700, fontSize: 18, color: PRIMARY }}>Kauvery Hospital</span>
        </div>
        <nav style={{ display: 'flex', gap: '2rem' }}>
          {['Home', 'Doctors', 'Contact'].map(link => (
            <a key={link} href="#" style={{ color: '#555', textDecoration: 'none', fontSize: 14, fontWeight: 500 }}>
              {link}
            </a>
          ))}
        </nav>
      </header>

      {/* ── Hero ─────────────────────────────────────────── */}
      <section style={{
        background: `linear-gradient(135deg, ${PRIMARY} 0%, #0052a3 100%)`,
        color: '#fff',
        padding: '5rem 2rem',
        textAlign: 'center',
      }}>
        <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3rem)', fontWeight: 800, margin: '0 0 1rem' }}>
          Your Health, Our Priority
        </h1>
        <p style={{ fontSize: '1.1rem', opacity: 0.88, maxWidth: 520, margin: '0 auto 2rem', lineHeight: 1.6 }}>
          World-class medical care, compassionate service, and cutting-edge
          technology — all under one roof at Kauvery Hospital.
        </p>
        <button
          onClick={openChat}
          style={{
            background: '#fff', color: PRIMARY,
            border: 'none', borderRadius: 30,
            padding: '0.85rem 2rem',
            fontSize: '1rem', fontWeight: 700,
            cursor: 'pointer',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            transition: 'transform 0.15s',
          }}
          onMouseEnter={e => e.target.style.transform = 'translateY(-2px)'}
          onMouseLeave={e => e.target.style.transform = 'translateY(0)'}
        >
          💬 Chat with Medibot
        </button>
      </section>

      {/* ── Feature cards ────────────────────────────────── */}
      <section style={{ padding: '4rem 2rem', maxWidth: 1000, margin: '0 auto' }}>
        <h2 style={{ textAlign: 'center', color: PRIMARY, marginBottom: '2.5rem', fontWeight: 700, fontSize: '1.6rem' }}>
          Why Choose Kauvery?
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
          {[
            { icon: '🤖', title: '24/7 AI Support', desc: 'Medibot is always available — get instant medical guidance any time of day or night.' },
            { icon: '👨‍⚕️', title: 'Expert Specialists', desc: 'World-class doctors across Cardiology, Neurology, General Medicine and more.' },
            { icon: '📅', title: 'Easy Appointment Booking', desc: 'Book appointments in minutes through our intelligent chat assistant.' },
          ].map(card => (
            <div key={card.title} style={{
              background: '#fff',
              borderRadius: 12,
              padding: '2rem',
              boxShadow: '0 2px 12px rgba(0,102,204,0.07)',
              border: '1px solid #e5e9f0',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>{card.icon}</div>
              <h3 style={{ color: PRIMARY, marginBottom: '0.6rem', fontWeight: 700 }}>{card.title}</h3>
              <p style={{ color: '#666', lineHeight: 1.6, fontSize: 14, margin: 0 }}>{card.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────── */}
      <footer style={{
        background: '#1a2332', color: '#aab', textAlign: 'center',
        padding: '1.5rem', fontSize: 13,
      }}>
        © 2026 Kauvery Hospital. All rights reserved. |{' '}
        <span style={{ color: '#fff' }}>Emergency: 044-4000-6000</span>
      </footer>

      {/* ── Chat UI ──────────────────────────────────────── */}
      {chatOpen && (
        <ChatWindow
          onClose={() => setChatOpen(false)}
          onBotMessage={handleNewBotMessage}
        />
      )}
      <ChatWidget
        isOpen={chatOpen}
        onToggle={() => chatOpen ? setChatOpen(false) : openChat()}
        hasUnread={hasUnread}
      />
    </div>
  )
}
