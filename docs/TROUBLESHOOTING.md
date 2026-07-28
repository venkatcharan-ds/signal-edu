# Troubleshooting

## Authentication

### "Invalid login credentials" or OAuth error after GitHub sign-in

**Cause**: GitHub OAuth App callback URL doesn't match Supabase config.

**Fix**:
1. GitHub OAuth App → Authorization callback URL must be exactly:
   `https://ybrdpzdxczqditjeyail.supabase.co/auth/v1/callback`
2. Supabase → Authentication → URL Configuration → Redirect URLs must include:
   `https://signal-edu.vercel.app/auth/callback`
3. Supabase → Authentication → Providers → GitHub must be enabled with the correct Client ID and Secret.

---

### Stuck on `/auth/syncing` (spinner never stops)

**Cause**: Backend is not responding, or `NEXT_PUBLIC_API_URL` is wrong.

**Fix**:
1. Check backend health: `curl https://YOUR-RENDER-URL.onrender.com/health`
2. If health check fails, check Render logs for startup errors.
3. Verify `NEXT_PUBLIC_API_URL` in Vercel env vars matches the Render URL (including `/v1` suffix).
4. On Render free tier, the first request after inactivity takes 30–60 seconds (cold start). Wait and retry.

---

### "Session expired" on page load

**Cause**: Supabase session cookie expired or `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` are wrong.

**Fix**: Re-verify both values in Vercel env vars against the Supabase Settings → API page.

---

## Analysis pipeline

### Analysis stuck on "pending" or "running" indefinitely

**Cause**: Backend process crashed or hit an unhandled error.

**Fix**:
1. Check Render logs for the specific error.
2. Common causes: `ANTHROPIC_API_KEY` invalid/expired, `SUPABASE_SERVICE_ROLE_KEY` wrong, `DATABASE_URL` wrong format.
3. Verify `DATABASE_URL` uses the transaction pooler format with `postgresql+asyncpg://` prefix.

---

### Analysis fails with "rate limit exceeded"

**Cause**: Anthropic API rate limit hit.

**Fix**: The pipeline has built-in retry with exponential backoff. If it persists, check your Anthropic usage dashboard.

---

### Analysis completes but profile shows no scores

**Cause**: The user's public repos may have very little activity (< 5 commits total), or all repos are forks without original code.

**Expected behavior**: SIGNAL requires at least some original public repository activity to produce meaningful scores. This is intentional — it's not a bug.

---

## Frontend / Vercel

### Build fails on Vercel

**Cause**: Usually TypeScript errors or missing environment variables.

**Fix**:
1. Check Vercel build logs for the exact error.
2. Run `npx tsc --noEmit` locally in `frontend/` to catch type errors before pushing.
3. Ensure all `NEXT_PUBLIC_*` vars are set in Vercel (not just local `.env.local`).

---

### CSP violations in browser console

**Cause**: A new external domain was added that isn't in the `connect-src` policy in `vercel.json`.

**Fix**: Add the domain to the `Content-Security-Policy` header in `frontend/vercel.json`:

```json
"connect-src 'self' https://*.supabase.co wss://*.supabase.co https://*.onrender.com https://NEW-DOMAIN.com"
```

Then redeploy.

---

### `/profile/[username]` shows stale data

**Cause**: ISR cache. The public profile page revalidates every 60 seconds.

**Fix**: Wait 60 seconds and hard-refresh. If you need to force it in development, set `export const revalidate = 0` temporarily.

---

## Database / Supabase

### "permission denied for table" error in backend logs

**Cause**: Backend is using the anon key instead of the service_role key.

**Fix**: Verify `SUPABASE_SERVICE_ROLE_KEY` is set correctly in the Render environment. It's a different key from `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

---

### Migration fails

**Cause**: Usually a constraint or column type conflict.

**Fix**:
1. Check Supabase → SQL Editor → run the failing migration manually to see the error
2. For duplicate table errors: the migration was already applied — skip it
3. For RLS errors: ensure `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` runs before policy creation

---

## Local development

### `npm run dev` fails with "Cannot find module"

```bash
cd frontend && npm ci   # install from lock file, not npm install
```

### Backend fails to start with "relation does not exist"

The database migrations haven't been applied. Run the migration files in `database/migrations/` in order against your local Postgres, or run `supabase db push` if using local Supabase.

### `uvicorn` starts but requests return 500

Check the backend `.env` — all required variables must be set. `DEBUG=true` will show the full stack trace in the response for easier debugging locally.
