# Plum Claims Processor

An AI-powered health insurance claims processing system. Submit a claim with supporting documents and a multi-agent pipeline returns a decision — **Approved**, **Partial**, **Rejected**, or **Manual Review** — with a full audit trail.

![Stack](https://img.shields.io/badge/backend-FastAPI%20%2B%20Python-009688?style=flat-square) ![Stack](https://img.shields.io/badge/frontend-React%20%2B%20TypeScript-3178C6?style=flat-square) ![LLM](https://img.shields.io/badge/LLM-OpenRouter-7C3AED?style=flat-square)

---

## How it works

```
Upload documents
      │
      ▼
DocumentClassifierAgent   →  identifies document type (bill / prescription / lab report …)
      │
      ▼
DocumentValidatorAgent    →  checks required docs are present and legible  [early exit]
      │
      ▼
DocumentParserAgent       →  extracts structured data via LLM vision
                              (line items, diagnosis, patient name, amounts …)
      │
      ▼
CrossDocValidatorAgent    →  verifies patient name matches across all documents  [early exit]
      │
      ▼
PolicyEngine              →  deterministic rule checks
                              (waiting periods, sub-limits, exclusions, co-pay, fraud signals)
      │
      ▼
FraudDetectorAgent        →  scores anomalies (same-day duplicates, amount spikes …)
      │
      ▼
DecisionAgent             →  synthesises final decision with LLM reasoning
      │
      ▼
JSON result  +  full per-step trace log
```

**Models (via [OpenRouter](https://openrouter.ai)):**
| Task | Model |
|---|---|
| Document vision & extraction | `google/gemini-2.5-flash` |
| Policy reasoning & decision | `deepseek/deepseek-chat-v3-0324` |

**Key design decisions:**
- LLM for extraction and reasoning; pure Python for all policy rule evaluation (no hallucination risk on financial logic)
- Every agent appends to a shared `TraceLog` — full reconstruction of every decision always available
- Agent failure → confidence penalty + degraded flag; pipeline continues (graceful degradation)
- Policy rules loaded from `policy_terms.json` — zero hardcoded business logic in code

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2 async |
| Database | SQLite (local) · PostgreSQL via Neon (production) |
| LLM API | OpenRouter (`openai` SDK) |
| Frontend | React 18, TypeScript, Vite, React Router v6, Axios |

---

## Project structure

```
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py         # coordinates the full pipeline
│   │   ├── document_classifier.py
│   │   ├── document_validator.py
│   │   ├── document_parser.py
│   │   ├── cross_doc_validator.py
│   │   ├── fraud_detector.py
│   │   └── decision_agent.py
│   ├── engines/
│   │   └── policy_engine.py        # deterministic rule engine (no LLM)
│   ├── models/                     # Pydantic models
│   ├── services/
│   │   └── llm_client.py           # OpenRouter wrapper with retry
│   ├── main.py                     # FastAPI app & routes
│   ├── database.py                 # SQLAlchemy async setup
│   ├── config.py                   # env var loading
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── SubmitClaim.tsx     # new claim form with drag-and-drop upload
│   │   │   ├── ClaimsList.tsx      # searchable claims history table
│   │   │   ├── ClaimDetail.tsx     # decision detail + resubmit flow
│   │   │   └── TestCases.tsx       # run predefined test scenarios
│   │   ├── components/
│   │   │   ├── DecisionBadge.tsx
│   │   │   ├── DocUploadCard.tsx
│   │   │   ├── TraceTimeline.tsx
│   │   │   ├── Icon.tsx            # SVG icon library
│   │   │   └── ErrorBoundary.tsx
│   │   ├── api/client.ts
│   │   └── main.tsx                # shell layout (sidebar + topbar + routes)
│   └── vite.config.ts
├── policy_terms.json               # policy rules & member roster
├── test_cases.json                 # predefined test scenarios
└── tests/                          # pytest suite
```

---

## Local setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key (free to sign up, pay-per-use)

### 1. Clone

```bash
git clone https://github.com/Abhijay0306/PLUM-CLAIM.git
cd PLUM-CLAIM
```

### 2. Backend

```bash
cd backend

# Create and activate virtualenv
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

Create `backend/.env`:

```env
OPENROUTER_API_KEY=sk-or-...your-key-here...
DATABASE_URL=sqlite+aiosqlite:///./claims.db
POLICY_FILE=../policy_terms.json
```

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

Swagger UI → `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open → `http://localhost:5173`

### 4. Run tests

```bash
cd backend
pytest ../tests/ -v
```

---

## API reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/claims/submit` | Submit a new claim with documents |
| `GET` | `/claims` | List all claims · supports `?q=` search |
| `GET` | `/claims/{id}` | Get single claim with full trace |
| `POST` | `/claims/{id}/resubmit` | Reprocess with new documents (keeps same claim ID) |
| `GET` | `/members` | List policy roster members |
| `GET` | `/policy` | Full policy terms JSON |
| `GET` | `/test-cases` | List predefined test scenarios |
| `POST` | `/test-cases/{id}/run` | Run a specific test case |

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | — | Your OpenRouter API key |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./claims.db` | SQLAlchemy async DB URL |
| `POLICY_FILE` | No | `../policy_terms.json` | Path to policy terms file |

For PostgreSQL, use:
```
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
```

---

## Deployment

### Overview

| Service | Purpose | Cost |
|---|---|---|
| [Vercel](https://vercel.com) | React frontend | Free |
| [Render](https://render.com) | FastAPI backend | Free (750 hrs/month) |
| [Neon](https://neon.tech) | PostgreSQL database | Free (0.5 GB) |
| [OpenRouter](https://openrouter.ai) | LLM API | Pay-per-use (~$0.001 per claim) |

---

### Step 1 — Database (Neon)

1. Sign up at [neon.tech](https://neon.tech) → **New Project** → name it `plum-claims`
2. Copy the **Connection string** from the dashboard

> It looks like: `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

---

### Step 2 — Backend (Render)

**Add `asyncpg` to `backend/requirements.txt`:**
```
asyncpg>=0.29.0
```

Push this change to GitHub, then:

1. Sign up at [render.com](https://render.com) → connect your GitHub account
2. **New → Web Service** → select the `PLUM-CLAIM` repository
3. Configure:

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

4. Add **Environment Variables**:

| Key | Value |
|---|---|
| `OPENROUTER_API_KEY` | your OpenRouter key |
| `DATABASE_URL` | Neon URL from Step 1, with `postgresql://` replaced by `postgresql+asyncpg://` |
| `POLICY_FILE` | `../policy_terms.json` |

5. Click **Create Web Service** → wait ~3 minutes for the first deploy
6. Note your backend URL: `https://plum-claims-api.onrender.com`

> **Free tier note:** Render free instances sleep after 15 min of inactivity. The first request after sleep takes ~30 seconds. This is expected.

---

### Step 3 — Frontend (Vercel)

Create `frontend/vercel.json` (replace the URL with your actual Render URL):

```json
{
  "rewrites": [
    {
      "source": "/claims/:path*",
      "destination": "https://plum-claims-api.onrender.com/claims/:path*"
    },
    {
      "source": "/policy",
      "destination": "https://plum-claims-api.onrender.com/policy"
    },
    {
      "source": "/members",
      "destination": "https://plum-claims-api.onrender.com/members"
    },
    {
      "source": "/health",
      "destination": "https://plum-claims-api.onrender.com/health"
    },
    {
      "source": "/test-cases/:path*",
      "destination": "https://plum-claims-api.onrender.com/test-cases/:path*"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

Commit and push this file, then:

1. Sign up at [vercel.com](https://vercel.com) → **Add New Project**
2. Import the `PLUM-CLAIM` repository
3. Set **Root Directory** to `frontend`
4. Framework preset auto-detects as **Vite** — leave defaults
5. Click **Deploy**

Your app is live at `https://plum-claim-xxx.vercel.app` 🎉

---

### Step 4 — Verify

1. Open your Vercel URL
2. Go to **Submit Claim** → enter member ID `EMP001`, upload any document, submit
3. Go to **Test Cases** → click **Run** on any scenario
4. If both work, the full stack is connected

---

### Updating the app

Both Vercel and Render auto-deploy on push to `main`:

```bash
git add .
git commit -m "your change"
git push origin main
```
