# Medibot — Kauvery Hospital AI Chatbot

A demo-ready POC chatbot for Kauvery Hospital. Patients interact through a floating chat widget on the hospital's landing page to identify themselves, describe symptoms, receive AI-guided triage, and book appointments — all in one conversational flow.

---

## Features

- **Patient identification** — returning patients look up by mobile number; new patients register inline
- **Emergency triage** — detects high-priority symptoms (chest pain, stroke, severe bleeding) and fast-tracks to an emergency doctor
- **Symptom collection** — dynamic follow-up questions, severity scoring, allergy and medication checks
- **RAG-powered guidance** — ChromaDB retrieval augments Claude's responses with Kauvery's medical knowledge base
- **Appointment booking** — recommends a specialist, shows real available slots from the DB, and confirms the booking
- **Unread message indicator** — floating chat button shows a badge when new bot messages arrive while chat is closed

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Django 4 + Django REST Framework    |
| Frontend   | React (Vite)                        |
| Database   | PostgreSQL                          |
| Vector DB  | ChromaDB (embedded)                 |
| AI Model   | Claude API (`claude-sonnet-4-20250514`) |
| Deployment | Render (free tier)                  |

---

## Project Structure

```
medibot/
├── backend/
│   ├── config/              # Django settings, URLs, WSGI
│   ├── apps/
│   │   ├── chat/            # Orchestrator, prompts, conversation models
│   │   ├── patients/        # Patient model
│   │   ├── doctors/         # Doctor, Department, Slot models
│   │   └── rag/             # ChromaDB loader and query
│   ├── data/
│   │   ├── seed.json        # Seed data for doctors and slots
│   │   └── medical_knowledge.txt
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Hospital landing page
│   │   ├── ChatWidget.jsx   # Floating chat button (bottom-right)
│   │   ├── ChatWindow.jsx   # Chat messages and input
│   │   └── api.js           # Backend API calls
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── render.yaml
```

---

## How It Works

The LLM drives the entire conversation. A lightweight state machine (`identify → emergency_check → symptoms → triage → booking → done`) only tracks progress — Claude decides what to say and when to advance.

Every Claude response includes a hidden metadata block:

```
|||METADATA|||
{"next_state": "symptoms", "context_updates": {"patient_name": "Alice"}}
|||END|||
```

The orchestrator strips this block, updates session state, and returns clean text to the frontend.

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL running locally
- Anthropic API key

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env`:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:5432/kauvery
ANTHROPIC_API_KEY=sk-ant-...
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

```bash
python manage.py migrate
python manage.py loaddata data/seed.json
python manage.py runserver     # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat/sessions/` | Create a new chat session |
| `POST` | `/api/chat/sessions/<token>/messages/` | Send a message, receive AI reply + state |
| `GET`  | `/api/chat/sessions/<token>/` | Fetch session history |
| `GET`  | `/api/doctors/` | List all doctors |
| `GET`  | `/api/doctors/<id>/slots/` | Get available slots for a doctor |
| `POST` | `/api/appointments/` | Book an appointment |

---

## Deployment (Render)

The project includes a `render.yaml` for one-click deployment:

- **Backend** — Python web service; build command: `pip install -r requirements.txt && python manage.py migrate`
- **Frontend** — Static site; build command: `npm run build`, publish directory: `dist/`
- **Database** — Render PostgreSQL (free tier)
- **ChromaDB** — embedded inside the backend container (no separate service needed)

---

## Disclaimer

This is a proof-of-concept demo. Medibot is not a licensed medical professional. All health guidance includes the disclaimer: *"I am not a doctor. Please consult a qualified physician."*

---

## License

MIT
