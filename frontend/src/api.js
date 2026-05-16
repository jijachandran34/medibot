const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function createSession() {
  const stored = localStorage.getItem('kauvery_session')
  if (stored) return stored

  const res = await fetch(`${API_BASE}/api/chat/sessions/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new Error(`Session create failed: ${res.status}`)
  const data = await res.json()
  localStorage.setItem('kauvery_session', data.session_token)
  return data.session_token
}

export async function sendMessage(token, message) {
  const res = await fetch(`${API_BASE}/api/chat/sessions/${token}/messages/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`Send failed: ${res.status}`)
  return res.json()
}

export async function getSession(token) {
  const res = await fetch(`${API_BASE}/api/chat/sessions/${token}/`)
  if (!res.ok) throw new Error(`Get session failed: ${res.status}`)
  return res.json()
}
