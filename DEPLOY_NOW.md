# SIGNAL EDU — Deploy Now

Everything is done except pushing to GitHub and setting secrets.
Follow these steps in order.

---

## 1. Push to GitHub (5 minutes)

```bash
# On GitHub.com: New repository → name "signal-edu" → Private → Create
# Then back here:

cd D:\DEVELOPMENT\PROJECTS\SIGNAL\signal

git remote add origin https://github.com/YOUR_USERNAME/signal-edu.git
git branch -M main
git push -u origin main
```

---

## 2. Deploy to Vercel (10 minutes)

1. Go to [vercel.com/new](https://vercel.com/new)
2. **Import Git Repository** → select `signal-edu`
3. **Root Directory** → `frontend`
4. **Framework Preset** → Next.js (auto-detected)
5. **Build Command** → `npm run build` (auto)
6. **Install Command** → `npm ci` (auto)

### Environment Variables to add in Vercel:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://ybrdpzdxczqditjeyail.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlicmRwemR4Y3pxZGl0amV5YWlsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA3NjYwMjQsImV4cCI6MjA5NjM0MjAyNH0.CCtLqYuZoaAm9g5EX4GQXIGHCMfvdU_6etkk2IgrUG0` |
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RENDER-URL.onrender.com/v1` ← update after Render deploy |

6. Click **Deploy**

### After first deploy, get your Vercel URL (e.g. `https://signal-edu.vercel.app`)

---

## 3. Configure Supabase Auth (10 minutes)

Go to [supabase.com/dashboard/project/ybrdpzdxczqditjeyail](https://supabase.com/dashboard/project/ybrdpzdxczqditjeyail)

### 3a. Enable GitHub OAuth

Authentication → Providers → GitHub → Enable

- **Client ID**: from your GitHub OAuth App (step below)
- **Client Secret**: from your GitHub OAuth App
- **Callback URL**: `https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback`

### 3b. Create GitHub OAuth App

Go to [github.com/settings/applications/new](https://github.com/settings/applications/new):

- **Application name**: `SIGNAL EDU`
- **Homepage URL**: `https://signal-edu.vercel.app`
- **Authorization callback URL**: `https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback`

Copy Client ID + generate Client Secret → paste into Supabase GitHub provider.

### 3c. Set Supabase Auth URLs

Authentication → URL Configuration:

- **Site URL**: `https://signal-edu.vercel.app`
- **Redirect URLs**: add `https://signal-edu.vercel.app/auth/callback`

---

## 4. Get Supabase Secrets (for backend)

Settings → API:

| Secret | Where |
|--------|-------|
| `SUPABASE_SERVICE_ROLE_KEY` | service_role key |
| `SUPABASE_JWT_SECRET` | JWT Settings → JWT Secret |

Connection strings → Transaction pooler → copy as `DATABASE_URL`
(format: `postgresql+asyncpg://postgres.ybrdpzdxczqditjeyail:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres`)

---

## 5. Deploy Backend to Render (separate step)

When deploying to Render, set these environment variables:

```
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=https://ybrdpzdxczqditjeyail.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_REDIRECT_URI=https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_CAPABILITY=claude-sonnet-4-5
ANTHROPIC_MODEL_RECOMMENDATION=claude-haiku-4-5-20251001
FRONTEND_URL=https://signal-edu.vercel.app
DAILY_ANALYSIS_LIMIT=3
ADMIN_API_KEY=
```

Render settings:
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`

After deploy → copy Render URL → update `NEXT_PUBLIC_API_URL` in Vercel → redeploy.

---

## 6. Post-deploy verification

```bash
# Backend health
curl https://YOUR-RENDER-URL.onrender.com/health

# Public profile (after running analysis)
curl https://YOUR-RENDER-URL.onrender.com/v1/profiles/YOUR_GITHUB_USERNAME

# Frontend
open https://signal-edu.vercel.app
```

End-to-end flow:
1. Land on signal-edu.vercel.app → landing page
2. Click "Get profile" → GitHub OAuth → /auth/callback → /auth/syncing → /dashboard
3. Click "Start analysis" → pipeline runs → profile generated
4. Visit /profile → scores and evidence citations
5. Visit /gaps → role comparison
6. Visit /recommendations → action items
7. Visit /profile/YOUR_USERNAME while logged out → public profile

---

## OAuth scopes (enforced in code)

Only these scopes are requested — no write access ever:
- `read:user` — username, avatar, name
- `public_repo` — public repository list and metadata
