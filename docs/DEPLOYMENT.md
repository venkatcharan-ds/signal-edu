# Production Deployment

SIGNAL deploys as three independent services:

| Service | Platform | Directory |
|---|---|---|
| Frontend | Vercel | `frontend/` |
| Backend | Render | `backend/` |
| Database + Auth | Supabase | hosted |

---

## 1. GitHub Repository

```bash
cd signal

# Create repo on github.com → New repository → "signal-edu" → Private → Create
git remote add origin https://github.com/YOUR_USERNAME/signal-edu.git
git branch -M main
git push -u origin main
```

---

## 2. Supabase (already configured)

Project: `https://ybrdpzdxczqditjeyail.supabase.co`

### Auth configuration

Authentication → URL Configuration:

- **Site URL**: `https://signal-edu.vercel.app`
- **Redirect URLs**: `https://signal-edu.vercel.app/auth/callback`

### GitHub OAuth provider

Authentication → Providers → GitHub → Enable:

- **Client ID**: from your GitHub OAuth App
- **Client Secret**: from your GitHub OAuth App
- **Callback URL** (read-only): `https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback`

### Secrets needed for backend

Settings → API:

| Variable | Location |
|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | API page → service_role key |
| `SUPABASE_JWT_SECRET` | JWT Settings → JWT Secret |
| `DATABASE_URL` | Settings → Database → Connection string → Transaction pooler (asyncpg format) |

---

## 3. GitHub OAuth Application

[github.com/settings/applications/new](https://github.com/settings/applications/new)

| Field | Value |
|---|---|
| Application name | `SIGNAL EDU` |
| Homepage URL | `https://signal-edu.vercel.app` |
| Authorization callback URL | `https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback` |

Copy Client ID + generate Client Secret → paste into Supabase GitHub provider.

---

## 4. Vercel (Frontend)

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import `signal-edu` from GitHub
3. **Root Directory**: `frontend`
4. Framework: Next.js (auto-detected)

### Environment variables

| Name | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://ybrdpzdxczqditjeyail.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (full key in DEPLOY_NOW.md) |
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RENDER-URL.onrender.com/v1` ← fill after Render deploy |
| `NEXT_PUBLIC_SITE_URL` | `https://signal-edu.vercel.app` |

Click **Deploy**.

---

## 5. Render (Backend)

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect GitHub → select `signal-edu`
3. **Root Directory**: `backend`
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
6. **Instance type**: Free (or Starter for always-on)

### Environment variables

```
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://postgres.ybrdpzdxczqditjeyail:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://ybrdpzdxczqditjeyail.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<from Supabase Settings → API>
SUPABASE_JWT_SECRET=<from Supabase Settings → JWT>
GITHUB_CLIENT_ID=<from GitHub OAuth App>
GITHUB_CLIENT_SECRET=<from GitHub OAuth App>
GITHUB_REDIRECT_URI=https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_CAPABILITY=claude-sonnet-4-5
ANTHROPIC_MODEL_RECOMMENDATION=claude-haiku-4-5-20251001
FRONTEND_URL=https://signal-edu.vercel.app
DAILY_ANALYSIS_LIMIT=3
ADMIN_API_KEY=
```

After deploy, copy the Render URL (e.g. `https://signal-edu-api.onrender.com`) and:

- Update `NEXT_PUBLIC_API_URL` in Vercel to `https://signal-edu-api.onrender.com/v1`
- Trigger a Vercel redeploy

---

## 6. Verify end-to-end

```bash
# Backend health
curl https://YOUR-RENDER-URL.onrender.com/health

# Frontend
open https://signal-edu.vercel.app
```

Full user flow:
1. `signal-edu.vercel.app` → landing page
2. "Get profile" → GitHub OAuth → `/auth/callback` → `/auth/syncing` → `/dashboard`
3. "Start analysis" → pipeline runs → profile generated
4. `/profile` → scores with evidence citations
5. `/gaps` → gap analysis vs. target role
6. `/recommendations` → action items
7. `/profile/[username]` while logged out → public profile (no auth required)

---

## Rollback

- **Frontend**: Vercel → Deployments → click any previous deployment → Redeploy
- **Backend**: Render → Manual Deploy → select commit
- **Database**: Supabase has point-in-time recovery on paid plans; on free tier, restore from migration files
