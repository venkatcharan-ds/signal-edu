# Local Development Setup

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Node.js | 20+ | `node --version` |
| Python | 3.12+ | `python --version` |
| Git | any | |
| Docker Desktop | latest | For local Postgres (optional) |

---

## 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/signal-edu.git
cd signal-edu
```

---

## 2. Supabase (database + auth)

For local development, you can either:

**Option A — Use the production Supabase project** (easiest, only one Supabase project)
- Skip this section; use the values from `.env.example` directly.

**Option B — Run Supabase locally** (isolated, requires Docker)

```bash
npm install -g supabase
supabase start
# Copy the URL and anon key printed to terminal
```

Apply migrations:

```bash
supabase db push
# or manually run files in database/migrations/ in order
```

---

## 3. Backend

```bash
cd backend
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

Copy and fill in the env file:

```bash
cp .env.example .env
```

Minimum required values for local dev:

```env
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/postgres
SUPABASE_URL=https://ybrdpzdxczqditjeyail.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your service_role key>
SUPABASE_JWT_SECRET=<your JWT secret>
GITHUB_CLIENT_ID=<your OAuth app client ID>
GITHUB_CLIENT_SECRET=<your OAuth app client secret>
GITHUB_REDIRECT_URI=https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_CAPABILITY=claude-sonnet-4-5
ANTHROPIC_MODEL_RECOMMENDATION=claude-haiku-4-5-20251001
FRONTEND_URL=http://localhost:3000
DAILY_ANALYSIS_LIMIT=3
```

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI (development only): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 4. Frontend

```bash
cd frontend
npm ci
cp .env.local.example .env.local
```

Fill in `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://ybrdpzdxczqditjeyail.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
NEXT_PUBLIC_API_URL=http://localhost:8000/v1
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

Start the frontend:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## 5. GitHub OAuth App (for sign-in to work locally)

1. Go to [github.com/settings/applications/new](https://github.com/settings/applications/new)
2. Application name: `SIGNAL EDU (local)`
3. Homepage URL: `http://localhost:3000`
4. Authorization callback URL: `https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback`
5. Copy Client ID + Secret → set in backend `.env` as `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`
6. In Supabase: Authentication → Providers → GitHub → paste the same values

---

## 6. Verify

```bash
# Backend health
curl http://localhost:8000/health

# Frontend
open http://localhost:3000
```

Full sign-in flow: landing → "Get profile" button → GitHub OAuth → /auth/callback → /auth/syncing → /dashboard.

---

## Useful commands

```bash
# Run backend tests
cd backend && pytest

# Type-check frontend
cd frontend && npx tsc --noEmit

# Lint frontend
cd frontend && npm run lint

# Production build (local)
cd frontend && npm run build && npm start
```
