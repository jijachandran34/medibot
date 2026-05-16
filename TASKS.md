# Kauvery Medibot — Task Tracker
# Status: 🔴 TODO | 🟡 IN PROGRESS | ✅ DONE | ❌ BLOCKED
# One task at a time. Test before moving on.

---

## SESSION STARTER — paste this at the start of every Claude Code session

```
Read CLAUDE.md and TASKS.md.
Find the first 🟡 IN PROGRESS task.
Show me what files exist related to that task before changing anything.
Then fix ONLY that task.
Tell me exactly what changed and how to test it (use PowerShell commands).
```

---

## CURRENT TASK → TASK-010

---

### ✅ TASK-001 — Project Scaffold

**What to build:**
Create the full folder structure and base configuration for a clean restart.
Delete or ignore any previous code.

**Exact structure to create:**
```
kauvery-medibot/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py        ← see requirements below
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── chat/              ← Django app
│   │   ├── patients/          ← Django app
│   │   ├── doctors/           ← Django app
│   │   └── rag/               ← Django app
│   ├── data/
│   │   └── medical_knowledge.txt   ← placeholder file, add 10 sample symptom entries
│   ├── manage.py
│   └── requirements.txt       ← see below
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── ChatWidget.jsx
│   │   ├── ChatWindow.jsx
│   │   └── api.js
│   ├── index.html
│   └── package.json
├── docker-compose.yml
├── CLAUDE.md
└── TASKS.md
```

**requirements.txt must include:**
```
django>=4.2
djangorestframework
django-cors-headers
psycopg2-binary
anthropic
chromadb
python-dotenv
gunicorn
whitenoise
```

**settings.py must have:**
- INSTALLED_APPS includes all 4 apps + rest_framework + corsheaders
- DATABASE from DATABASE_URL env var (use dj-database-url)
- ANTHROPIC_API_KEY loaded from env
- CORS configured for localhost:5173
- Static files configured with whitenoise (for Render)

**package.json must use:**
- React + Vite
- No extra UI libraries — plain CSS only

**Do NOT create models yet — that is TASK-002.**

**Test:**
```powershell
# Backend starts clean
cd backend
python manage.py check
# Expected: System check identified no issues

# Frontend installs
cd frontend
npm install
npm run dev
# Expected: Vite dev server starts on localhost:5173
```

**Done when:** Both commands pass with no errors.

---

### ✅ TASK-002 — Django Models + Migrations

**What:** Create all models exactly as defined in CLAUDE.md.

**Files to create/edit:**
- `apps/patients/models.py` → Patient
- `apps/doctors/models.py` → Department, Doctor, Slot
- `apps/chat/models.py` → Conversation (with STATE_CHOICES for all 6 states), Message, Appointment

**STATE_CHOICES must be exactly:**
```python
STATE_CHOICES = [
    ('identify', 'Identify Patient'),
    ('emergency_check', 'Emergency Check'),
    ('symptoms', 'Symptom Collection'),
    ('triage', 'Triage & Guidance'),
    ('booking', 'Appointment Booking'),
    ('done', 'Done'),
]
```

**Test:**
```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py shell -c "from apps.chat.models import Conversation; print([s[0] for s in Conversation.STATE_CHOICES])"
# Expected: ['identify', 'emergency_check', 'symptoms', 'triage', 'booking', 'done']
```

**Done when:** Migration runs clean, all 6 states confirmed in shell.

---

### ✅ TASK-003 — Seed Data

**What:** Create `data/seed.json` with mock data:
- 3 departments: General Medicine, Cardiology, Neurology
- 5 doctors (mix across departments)
- 10 available slots (spread across next 7 days)
- 2 sample patients

**Test:**
```powershell
python manage.py loaddata data/seed.json
python manage.py shell -c "from apps.doctors.models import Doctor; print(Doctor.objects.count())"
# Expected: 5
```

**Done when:** Seed loads clean, 5 doctors confirmed.

---

### ✅ TASK-004 — Core Chat API Endpoints

**What:** Create these endpoints in `apps/chat/views.py` and `apps/chat/urls.py`:

```
POST /api/chat/sessions/                    → creates Conversation, returns session_token
POST /api/chat/sessions/<token>/messages/   → stub: echoes message back, state stays 'identify'
GET  /api/chat/sessions/<token>/            → returns session + message history
```

**Important:** The message endpoint is a STUB here — just echo the message.
Claude API integration comes in TASK-005. Keep views.py simple.

**Test:**
```powershell
# Create session
$r = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/chat/sessions/" -ContentType "application/json"
$TOKEN = $r.session_token
Write-Host $TOKEN

# Send message (stub echo)
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/chat/sessions/$TOKEN/messages/" `
  -ContentType "application/json" -Body '{"message": "hi"}'
# Expected: {session_token, message: "hi", state: "identify"}

# Get history
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/api/chat/sessions/$TOKEN/"
# Expected: session object with messages array
```

**Done when:** All 3 test commands return valid JSON with no errors.

---

### ✅ TASK-005 — Claude API Orchestrator

**What:** Replace the stub in `views.py` with real Claude API integration.
Create `apps/chat/orchestrator.py` and `apps/chat/prompts.py`.

**orchestrator.py must:**
1. Accept (conversation, user_message)
2. Build system prompt using current state + RAG context (empty for now) + collected context
3. Call Claude API with full message history
4. Parse |||METADATA||| block from response
5. Update conversation state + context from metadata
6. Return clean response text (metadata stripped)

**prompts.py must:**
- Have a `build_system_prompt(state, rag_context, context)` function
- Have one system prompt section per state (identify, emergency_check, symptoms, triage, booking, done)
- Include the metadata format instruction in every prompt

**Metadata format Claude must return:**
```
|||METADATA|||
{"next_state": "emergency_check", "context_updates": {"patient_name": "John", "patient_age": 35}}
|||END|||
```

**Test:**
```powershell
$r = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/chat/sessions/" -ContentType "application/json"
$TOKEN = $r.session_token

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/chat/sessions/$TOKEN/messages/" `
  -ContentType "application/json" -Body '{"message": "hi"}'
# Expected: state=identify, Claude asks new or existing patient

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/chat/sessions/$TOKEN/messages/" `
  -ContentType "application/json" -Body '{"message": "new patient, my name is Ravi, 35 years old, male, 9876543210"}'
# Expected: state=emergency_check, Claude asks about emergency symptoms

Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/chat/sessions/$TOKEN/messages/" `
  -ContentType "application/json" -Body '{"message": "no emergency"}'
# Expected: state=symptoms, Claude asks about symptoms
```

**Done when:** All 3 states transition correctly in sequence.

---

### ✅ TASK-006 — RAG Pipeline

**What:** Wire ChromaDB into the orchestrator for symptom/triage states.
Create `apps/rag/loader.py` and `apps/rag/query.py`.

**loader.py:** Reads `data/medical_knowledge.txt`, splits into chunks, loads into ChromaDB collection named "medical_knowledge"

**query.py:** Takes a symptom string, returns top 3 relevant chunks from ChromaDB

**medical_knowledge.txt** should have at least 15 entries covering:
- Common cold, flu, fever
- Headache, migraine
- Chest pain (emergency)
- Stomach pain, nausea
- Back pain
- Allergic reactions
- Diabetes symptoms
- Hypertension symptoms
- OTC suggestions (paracetamol, antacids, ORS)
- Home remedies (rest, hydration, steam)

**Integration:** In orchestrator.py, when state is 'symptoms' or 'triage', call `query_rag(user_message)` and inject result into system prompt.

**Test:**
```powershell
# Load RAG data
python manage.py shell -c "from apps.rag.loader import load_knowledge; load_knowledge(); print('RAG loaded')"

# Query RAG
python manage.py shell -c "from apps.rag.query import query_rag; print(query_rag('fever and headache'))"
# Expected: 2-3 relevant text chunks returned
```

**Done when:** RAG query returns relevant results for common symptoms.

---

### ✅ TASK-007 — Appointment Booking via Chat

**What:** When state='booking', the orchestrator should:
1. Query available slots from DB
2. Inject slot data into the system prompt (as structured text)
3. Claude presents options to user
4. User picks a slot → orchestrator creates Appointment record in DB

**Add endpoint:**
```
GET /api/doctors/                     → list all doctors with department
GET /api/doctors/<id>/slots/          → available (is_booked=False) slots
```

**Test:**
```powershell
# Check doctors endpoint
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/api/doctors/"
# Expected: list of 5 doctors

# Full flow test — continue from TASK-005 session
# After symptoms → triage → say "I want to book an appointment"
# Expected: Claude shows doctor options with slots
# After picking slot → Appointment created in DB

python manage.py shell -c "from apps.chat.models import Appointment; print(Appointment.objects.count())"
# Expected: 1
```

**Done when:** Appointment record created in DB after full chat flow.

---

### ✅ TASK-008 — React Frontend

**What:** Build the complete frontend in `frontend/src/`.

**App.jsx:**
- Simple Kauvery Hospital landing page
- Header with hospital name + logo placeholder
- Hero section: "Your Health, Our Priority"
- 3 feature cards: 24/7 Support, Expert Doctors, Easy Booking
- ChatWidget always visible bottom-right

**ChatWidget.jsx:**
- Floating circular button (bottom-right, fixed position)
- Kauvery blue color (#0066CC)
- Click opens/closes ChatWindow
- Show unread dot when closed

**ChatWindow.jsx:**
- 400px wide, 600px tall (full screen on mobile)
- Header: "Medibot — Kauvery Hospital"
- Message bubbles: user (right, blue), bot (left, grey)
- Quick reply buttons when provided
- Input box + send button
- Auto-scroll to latest message
- Emergency messages: red background, bold text
- Appointment confirmation: green card with details
- Loading indicator (3 dots) while waiting for reply

**api.js:**
- `createSession()` → POST /api/chat/sessions/
- `sendMessage(token, message)` → POST /api/chat/sessions/<token>/messages/
- Store session token in localStorage

**Styling:** Plain CSS (no Tailwind, no MUI) — clean, medical, professional

**Test:**
- Open http://localhost:5173
- Page loads with hospital landing page
- Chat button visible bottom-right
- Click opens chat window
- Can type and send messages
- Bot replies appear correctly
- Works on 375px mobile viewport (check with browser DevTools)

**Done when:** Full chat flow works in browser, mobile responsive confirmed.

---

### ✅ TASK-009 — Emergency Triage UI

**What:** When Claude returns emergency response, frontend must:
- Show message with red background + ⚠️ icon
- Show emergency doctor card (name, department, phone)
- Show two buttons: "Book Emergency Slot" and "Call Now: 044-XXXX-XXXX"

**In orchestrator.py:** When state transitions to 'booking' from 'emergency_check',
add `"is_emergency": true` to the API response.

**In ChatWindow.jsx:** Check `is_emergency` flag in response, render emergency UI.

**Test:**
- Start new chat
- Say "I have severe chest pain and cannot breathe"
- Expected: Red emergency message + doctor card + call button

**Done when:** Emergency path clearly visually distinct, doctor shown, call button present.

---

### 🟡 TASK-010 — Render Deployment Prep (skipping Docker)

**What:** Prepare project for direct Render deployment.
- render.yaml in project root
- backend/build.sh (installs deps, collectstatic, migrate, loads RAG)
- settings.py CSRF_TRUSTED_ORIGINS added
- .gitignore already complete
- frontend api.js already uses VITE_API_URL

**Done when:** Pushed to GitHub, both Render services deploy successfully, full chat flow works on live URL.

---

### 🔴 TASK-011 — Render Deployment

**What:** Deploy to Render free tier.

**Steps Claude should do:**
1. Create `render.yaml` with backend web service + frontend static site config
2. Create `backend/build.sh`: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
3. Update settings.py: ALLOWED_HOSTS, STATIC_ROOT, CSRF_TRUSTED_ORIGINS for Render URL
4. Update frontend api.js: use environment variable for API base URL (VITE_API_URL)

**Test:**
- Push to GitHub
- Connect repo to Render
- Both services deploy successfully
- Visit live URL, complete one full chat flow

**Done when:** Live demo URL works end-to-end.

---

### 🟡 TASK-011 — UI/UX Polish

**What:** Six UX improvements for the chat interface.

**Done:**
- FIX 1: Quick replies already cleared on click (setQuickReplies([]) in callSend)
- FIX 2: Booking slots shown as tappable buttons (orchestrator builds quick_replies for booking state)
- FIX 3: Emergency buttons styled red/green in ChatWindow.jsx
- FIX 4: Appointment reference KH00001 appended to booking confirmation reply
- FIX 5: Medication formatting with 💊/🏠 headers and • bullets in renderBubbleContent
- FIX 6: Disclaimer rendered in amber highlighted box (⚠️DISCLAIMER:...⚠️END parsing)

**Done when:** Push to GitHub, Render redeploys, all 6 items visible in browser.

---

### 🔴 TASK-012 — Full Demo Flow Test

**What:** Dry-run the complete demo script end-to-end.

**Demo script to test:**

```
1. Open live URL
2. Click chat widget
3. "Hi" → bot greets, asks new or existing
4. "New patient" → bot asks for details
5. "My name is Priya, 28 years old, female, 9876543210"
   → bot asks emergency check questions
6. "No emergency, I have a fever and headache for 2 days"
   → bot asks follow-up: severity? chills? existing conditions?
7. "Severity 4, no chills, no existing conditions"
   → bot gives RAG-based guidance (rest, hydration, paracetamol with disclaimer)
   → bot asks if I want to book an appointment
8. "Yes please book an appointment"
   → bot shows General Medicine doctors + slots
9. "Book Dr. [Name] on [Date] at [Time]"
   → bot confirms appointment with green card
10. Appointment exists in DB ✅
```

**Done when:** All 10 steps complete without errors on live Render URL.

---

## Completed Tasks Log

| Task | Done | Notes |
|------|------|-------|
| — | — | Fresh start |
