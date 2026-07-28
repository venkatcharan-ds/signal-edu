# SIGNAL EDU

**Evidence-based capability profiles for students.**

SIGNAL analyzes a student's GitHub activity and produces a structured, citable skill profile that surfaces the talent credentials can't capture.

> Built for the Cintana AI Challenge 2025.

---

## What it does

1. Student signs in with GitHub (read-only — `read:user public_repo`)
2. SIGNAL's analysis pipeline inspects repositories, commit history, and project artifacts
3. An AI scoring layer assigns capability scores across three dimensions:
   - **Technical Execution (TE)** — code quality, architecture, complexity
   - **Project Complexity (PC)** — scope, depth, sustained effort
   - **Conceptual Quality (CQ)** — design decisions, problem-solving
4. Every score is backed by a specific, citable artifact — no hallucinated claims
5. A shareable public profile page shows scores and evidence to anyone (no login required)

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router) + React 19 + Tailwind CSS v4 |
| Backend | FastAPI + Python 3.12 + SQLAlchemy (async) |
| Database | PostgreSQL via Supabase (RLS enabled) |
| Auth | Supabase Auth — GitHub OAuth with PKCE |
| AI | Anthropic Claude (Sonnet for capability analysis, Haiku for recommendations) |
| Frontend deploy | Vercel |
| Backend deploy | Render |

---

## Repository layout

```
signal/
├── frontend/          Next.js application
├── backend/           FastAPI application
├── database/          Migrations and seed data
├── docs/              Guides, architecture, deployment
├── scripts/           Utility scripts
└── docker-compose.yml Local development stack
```

---

## Quick start (local)

### Prerequisites

- Node.js 20+
- Python 3.12+
- Docker Desktop (for local Supabase or Postgres)

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/signal-edu.git
cd signal-edu
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in your values
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm ci
cp .env.local.example .env.local  # fill in your values
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Docs

| Document | Purpose |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Local development setup |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment (Vercel + Render) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) | End-to-end demo walkthrough |
| [docs/COMPETITION_GUIDE.md](docs/COMPETITION_GUIDE.md) | Cintana AI Challenge submission |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [DEPLOY_NOW.md](DEPLOY_NOW.md) | Fast-path production deploy checklist |

---

## Security

- **OAuth scopes**: `read:user public_repo` only — zero write access to any GitHub resource
- **Anti-hallucination**: AI scores are capped — TE cannot exceed 1.5 normalized points above the objective ceiling derived from repository metrics
- **Every claim is cited**: Each score requires a specific repository artifact as justification
- **RLS enforced**: All database tables have Row Level Security enabled; the backend uses a service-role key server-side only
- **No secrets on the client**: Only `NEXT_PUBLIC_` prefixed variables (Supabase URL + anon key) reach the browser

---

## License

MIT — see [LICENSE](LICENSE).
