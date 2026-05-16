# Kauvery Hospital Medibot — Project Memory
# Claude Code reads this file at the start of EVERY session.
# Do not delete. Update "Current Status" after each completed task.

---

## Project Goal

A demo-ready POC chatbot for Kauvery Hospital.
- Simple hospital webpage with a chat widget (bottom-right corner)
- Chatbot handles: patient identification → emergency check → symptoms → RAG guidance → appointment booking
- Deployable on Render (free tier)
- Architecture open for future scaling

---

## Tech Stack (FIXED — do not change)

| Layer        | Choice                                      |
|--------------|---------------------------------------------|
| Backend      | Django + Django REST Framework              |
| Frontend     | React (single page, chat widget only)       |
| Database     | PostgreSQL                                  |
| Vector DB    | ChromaDB (local, embedded)                  |
| AI Model     | Claude API (claude-sonnet-4-20250514)       |
| Deployment   | Render (free tier)                          |
| Auth         | None for POC (session token only)           |

---

## Architecture (simple, modular)

```
kauvery-medibot/
├── backend/
│   ├── config/                     # settings, urls, wsgi
│   ├── apps/
│   │   ├── chat/                   # orchestrator, prompts, views, models
│   │   ├── patients/               # Patient model
│   │   ├── doctors/                # Doctor, Department, Slot models
│   │   └── rag/                    # ChromaDB loader + query
│   ├── data/
│   │   ├── seed.json
│   │   └── medical_knowledge.txt
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Hospital landing page
│   │   ├── ChatWidget.jsx          # Floating button bottom-right
│   │   ├── ChatWindow.jsx          # Chat messages + input
│   │   └── api.js                  # API calls to backend
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── render.yaml
├── CLAUDE.md
└── TASKS.md
```

---

## Core Design Principle (CRITICAL — DO NOT CHANGE)

**The LLM (Claude API) drives the entire conversation.**
**The state machine only tracks progress.**

- No rule-based fallback system
- No competing logic
- One path: LLM response → parse metadata → update state

### Orchestrator flow (simple)

```python
def handle_message(session, user_message):
    rag_context = get_rag_context(user_message) if needed else ""
    system = build_system_prompt(session.state, rag_context, session.context)
    response = call_claude(system, session.messages + [user_message])
    metadata = parse_metadata(response)       # reads JSON block from Claude
    session.state = metadata.get('next_state', session.state)
    session.context.update(metadata.get('context_updates', {}))
    return clean_response_text(response), session.state
```

---

## Chatbot Flow (MANDATORY)

### STATE 1: identify
- Ask: existing or new patient?
- Existing → ask mobile/ID → look up DB → confirm
- New → collect name, age, gender, mobile
- Complete → next_state: "emergency_check"

### STATE 2: emergency_check
- Ask about: chest pain, breathing difficulty, unconsciousness, severe bleeding, stroke
- Emergency → alert + emergency doctor + fast-track → next_state: "booking"
- No emergency → next_state: "symptoms"

### STATE 3: symptoms
- Collect: symptom, duration, severity (1-10), allergies, conditions, medications
- Ask at least 2 dynamic follow-up questions before moving on
- Complete → next_state: "triage"

### STATE 4: triage
- Use RAG context
- Mild → home remedy + OTC with disclaimer + consent → next_state: "booking" or "done"
- Moderate/Severe → recommend specialist → next_state: "booking"
- ALWAYS include: "I am not a doctor. Please consult a qualified physician."

### STATE 5: booking
- Recommend department
- Show available doctors + slots from DB
- Confirm → create Appointment record → next_state: "done"

### STATE 6: done
- Confirm booking details
- Offer further help

---

## System Prompt Strategy

Tell Claude in system prompt:
1. You are Medibot, Kauvery Hospital's AI assistant
2. Current state: {state}
3. RAG context: {rag_context}
4. Patient context collected so far: {context}
5. Follow the flow rules for current state exactly
6. End EVERY response with this metadata block:
   |||METADATA|||
   {"next_state": "symptoms", "context_updates": {"patient_name": "John"}}
   |||END|||
7. Never skip states. Never re-ask collected info.
8. Always include medical disclaimer when giving health guidance.

---

## Database Models

```python
# patients/models.py
Patient: id, name, age, gender, mobile, created_at

# doctors/models.py
Department: id, name, description
Doctor: id, name, department, qualification, available_days
Slot: id, doctor, date, time, is_booked

# chat/models.py
Conversation: id, session_token, state, context(JSON), patient(FK nullable), created_at
Message: id, conversation(FK), role, content, created_at
Appointment: id, patient(FK), doctor(FK), slot(FK), reason, booked_at
```

---

## API Endpoints

```
POST /api/chat/sessions/                      → create session
POST /api/chat/sessions/<token>/messages/     → send message, get reply + state
GET  /api/chat/sessions/<token>/              → session history
GET  /api/doctors/                            → list doctors
GET  /api/doctors/<id>/slots/                 → available slots
POST /api/appointments/                       → book appointment
```

---

## Environment Variables

```
# backend/.env
SECRET_KEY=your-django-secret
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost:5432/kauvery
ANTHROPIC_API_KEY=sk-ant-...
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

---

## Local Setup

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata data/seed.json
python manage.py runserver   # runs on :8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                  # runs on :5173
```

---

## Render Deployment

- Backend: Python web service → `pip install -r requirements.txt && python manage.py migrate`
- Frontend: Static site → build: `npm run build`, publish: `dist/`
- Database: Render PostgreSQL (free tier)
- ChromaDB: embedded inside backend (no separate service)

---

## Current Status

- [x] TASK-001: Project scaffold
- [x] TASK-002: Django models + migrations
- [x] TASK-003: Seed data
- [x] TASK-004: Core chat API endpoints
- [~] TASK-005: Claude API orchestrator — state transitions need prompt tuning, fix in TASK-014
- [x] TASK-006: RAG pipeline (ChromaDB)
- [x] TASK-007: Appointment booking via chat
- [ ] TASK-008: Appointment booking via chat
- [x] TASK-008: React frontend (landing page + chat widget)
- [ ] TASK-010: Frontend ↔ backend connection
- [x] TASK-009: Emergency triage UI
- [ ] TASK-012: Docker + local end-to-end test
- [ ] TASK-013: Render deployment
- [ ] TASK-014: Full demo flow test

---

## Rules for Claude Code (always follow)

1. Read CLAUDE.md + TASKS.md at session start
2. Work on ONE task at a time — the first 🟡 IN PROGRESS task
3. Never touch completed ✅ tasks
4. Never refactor unrelated files
5. After every change: state what changed, which file, how to test
6. If fix needs more than 3 files — stop and ask first
7. Test commands must use PowerShell (Invoke-RestMethod) — Windows machine
8. Always use a new session token when retesting chat flows
