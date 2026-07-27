# SIGNAL EDU — Production Setup

## Order of operations

Complete these steps **in order**. Each stage has external dependencies that cannot be parallelized.

---

## Stage 1 — Supabase Production Project

### 1.1 Create project
1. Go to [supabase.com](https://supabase.com) → New Project
2. Choose region closest to your Railway deployment (e.g. `us-east-1`)
3. Save the **Project URL**, **anon key**, **service_role key**, and **JWT Secret** (Settings → API)

### 1.2 Enable GitHub OAuth
1. Supabase Dashboard → Auth → Providers → GitHub → Enable
2. Note the **Callback URL**: `https://[project-ref].supabase.co/auth/v1/callback`

### 1.3 Register GitHub OAuth App
1. Go to [github.com/settings/applications/new](https://github.com/settings/applications/new)
2. **Application name**: `SIGNAL EDU`
3. **Homepage URL**: `https://signal-edu.vercel.app` (your Vercel domain)
4. **Authorization callback URL**: the Supabase callback from 1.2
5. Click Register → copy **Client ID** and generate **Client Secret**
6. Paste both into Supabase → Auth → Providers → GitHub

### 1.4 Configure Supabase Auth URLs
1. Supabase → Auth → URL Configuration
2. **Site URL**: `https://signal-edu.vercel.app`
3. **Redirect URLs** → Add: `https://signal-edu.vercel.app/auth/callback`

### 1.5 Run database migrations
```bash
# From signal/backend/
DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head
```

Verify:
```sql
SELECT COUNT(*) FROM role_templates;  -- expect 10
```

---

## Stage 2 — Backend → Railway

### 2.1 Create Railway project
1. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select your repo; set **Root Directory** to `signal/` and **Dockerfile path** to `backend/Dockerfile`

### 2.2 Set environment variables
In Railway → Variables, add every variable from `.env.example` under the "Backend (Railway)" section.

Critical values:
- `ENVIRONMENT=production`
- `DEBUG=false`
- `FRONTEND_URL=https://signal-edu.vercel.app`

### 2.3 Generate public domain
Railway → Settings → Networking → Generate Domain

Copy the Railway URL (e.g. `signal-backend.up.railway.app`) — you need it for Vercel.

### 2.4 Verify
```
GET https://signal-backend.up.railway.app/health
→ {"status":"ok","version":"0.1.0","environment":"production"}

GET https://signal-backend.up.railway.app/docs
→ 404 (docs disabled in production)
```

---

## Stage 3 — Frontend → Vercel

### 3.1 Import project
1. [vercel.com](https://vercel.com) → New Project → import GitHub repo
2. **Root Directory**: `signal/frontend`
3. **Framework**: Next.js (auto-detected)

### 3.2 Set environment variables
In Vercel → Settings → Environment Variables, add the three frontend vars from `.env.example`.

Update `NEXT_PUBLIC_API_URL` to the Railway URL from Stage 2.3:
```
NEXT_PUBLIC_API_URL=https://signal-backend.up.railway.app/v1
```

### 3.3 Update vercel.json rewrite
Edit `frontend/vercel.json` → update the `destination` URL to your actual Railway domain.

### 3.4 Update CORS in Railway
Set `FRONTEND_URL` in Railway to the exact Vercel URL that was generated (e.g. `https://signal-edu.vercel.app`).

### 3.5 Deploy and verify
Vercel auto-deploys on push to main. After deploy:
1. Visit Vercel URL → landing page loads
2. Click "Sign in with GitHub" → OAuth works → dashboard loads
3. Run an analysis → pipeline completes
4. Visit `/profile/[your-username]` while logged out → real data shows

---

## Stage 4 — Post-deployment checks

```bash
# Backend health
curl https://signal-backend.up.railway.app/health

# Public profile (replace with a real username that has run an analysis)
curl https://signal-backend.up.railway.app/v1/profiles/[github-username]

# Rate limit check (requires auth token)
curl -H "Authorization: Bearer $TOKEN" \
  https://signal-backend.up.railway.app/v1/analysis/quota
```

---

## Environment variable reference

| Variable | Where | Required |
|---|---|---|
| `DATABASE_URL` | Railway | Yes |
| `SUPABASE_URL` | Railway | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Railway | Yes |
| `SUPABASE_JWT_SECRET` | Railway | Yes |
| `GITHUB_CLIENT_ID` | Railway | Yes |
| `GITHUB_CLIENT_SECRET` | Railway | Yes |
| `ANTHROPIC_API_KEY` | Railway | Yes |
| `FRONTEND_URL` | Railway | Yes |
| `ENVIRONMENT` | Railway | Yes (`production`) |
| `DEBUG` | Railway | Yes (`false`) |
| `DAILY_ANALYSIS_LIMIT` | Railway | No (default: 3) |
| `ADMIN_API_KEY` | Railway | No (disables admin if blank) |
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Vercel | Yes |
| `NEXT_PUBLIC_API_URL` | Vercel | Yes |
