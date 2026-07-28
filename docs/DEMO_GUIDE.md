# Demo Guide

End-to-end walkthrough for the SIGNAL EDU demo.

---

## Before the demo

- [ ] Backend is running (Render URL responds to `/health`)
- [ ] Frontend is live (`signal-edu.vercel.app` loads)
- [ ] Your GitHub account has at least 3–5 public repos with meaningful code
- [ ] You've run an analysis on your own account at least once (so the profile is ready)
- [ ] Browser is in a clean profile or incognito — no cached state
- [ ] Screen share is ready, browser zoom at 110%

---

## Demo script (8 minutes)

### 0:00 — The problem (30 seconds)

> "A student with a 3.8 GPA and a blank resume and a student with a 3.2 GPA and a GitHub full of real projects look identical to a hiring system. Transcripts can't surface actual capability. SIGNAL fixes that."

### 0:30 — Landing page (30 seconds)

Navigate to `https://signal-edu.vercel.app`.

Point out:
- The tagline: "We surface the talent that credentials hide"
- The three score dimensions: TE / PC / CQ
- The "Get profile" CTA

> "The entire entry point is one click — GitHub sign-in, read-only access only."

### 1:00 — GitHub OAuth (1 minute)

Click **"Get profile"**.

Walk through:
- The GitHub authorization screen — point out the exact scopes: `read:user` and `public_repo`
- "No write access. We can't touch any of your code."

After authorization → `/auth/syncing` → `/dashboard`.

### 2:00 — Dashboard (1 minute)

Point out:
- The user's GitHub identity pulled in (avatar, username)
- Existing profile scores if present, or the "Start analysis" button if first time
- The daily analysis limit counter (3 per day)

Click **"Start analysis"** if no profile exists yet.

### 3:00 — Analysis running (1 minute)

Show the analysis progress screen:
- Repositories being scanned (live update)
- "Analyzing [repo name]..." status messages

> "The pipeline is reading your public repos, scoring them on three dimensions, and finding specific artifacts to back every score."

### 4:00 — Capability Profile (2 minutes)

Navigate to `/profile`.

Walk through:
- The three score rings: TE, PC, CQ on the 1–9 scale
- Click one evidence citation — show the specific commit/file it links to
- "Every number here is backed by a real artifact in your repositories. Nothing is hallucinated."

Key talking point: **anti-hallucination cap**
> "The AI cannot inflate Technical Execution more than 1.5 points above what the repo metrics objectively support. The score has to be defensible."

### 6:00 — Gap Analysis (1 minute)

Navigate to `/gaps`.

- Select a target role (e.g., "Software Engineer", "ML Engineer")
- Show the delta view: where they stand vs. what the role requires
- "This tells a student exactly what to build next."

### 7:00 — Public Profile (30 seconds)

Open an incognito tab. Navigate to `https://signal-edu.vercel.app/profile/[your-github-username]`.

- The profile is fully public — shareable URL, no login required
- Show the scores and evidence
- "This is what a recruiter or program director sees."

### 7:30 — Closing (30 seconds)

> "SIGNAL gives students something credentials never could: a verifiable, evidence-backed capability profile built from real work. And it gives institutions and employers a signal they can actually trust."

---

## Backup demo plan

If the backend is down (Render cold start, etc.):

1. Open the pre-built public profile: `https://signal-edu.vercel.app/profile/[username]`
   - This is statically cached (ISR, 60s) — no backend needed to view it
2. Show screenshots of the analysis flow (keep in a Google Slides backup deck)
3. Walk through the architecture diagram in `docs/ARCHITECTURE.md`

If GitHub OAuth fails:
- Show the landing page + architecture
- Explain the flow verbally
- Show the public profile page (no auth required)

If Vercel is down:
- Run `npm run dev` locally and demo on `localhost:3000`
- Start the backend with `uvicorn app.main:app --reload`

---

## Demo data checklist

Before presenting, verify:

- [ ] `https://signal-edu.vercel.app` loads in < 2 seconds
- [ ] `https://YOUR-RENDER-URL.onrender.com/health` returns `{"status": "ok"}`
- [ ] Your own profile is pre-generated (`/profile` shows scores, not empty state)
- [ ] Gap analysis has a selected role with gap data visible
- [ ] Public profile URL `signal-edu.vercel.app/profile/[username]` loads without login
- [ ] At least one evidence citation links to a real repo artifact

---

## Talking points — judges questions

**"How do you prevent score inflation?"**
> The AI model is given the objective repo metrics (commit count, code size, language depth) before scoring. A hard cap prevents the TE score from going more than 1.5 normalized points above what the metrics support. Every score must cite a specific artifact.

**"Why GitHub and not a portfolio submission?"**
> GitHub is where students already do real work. We analyze existing behavior, not curated submissions. A student can't fake years of commit history.

**"What about students who don't have GitHub accounts?"**
> SIGNAL is designed for STEM students who use GitHub as part of their coursework. Version control adoption is part of what SIGNAL measures — it's a signal in itself.

**"How is this different from GitHub Profile Readme generators?"**
> Those summarize activity. SIGNAL evaluates capability across three structured dimensions and produces a structured, comparable profile — not a narrative. Two students can be ranked against each other and against role requirements.

**"What's the data privacy model?"**
> Only public repositories are analyzed. OAuth scopes are `read:user public_repo` — we can't see private repos or write anything. Users own their profile data and can delete it.
