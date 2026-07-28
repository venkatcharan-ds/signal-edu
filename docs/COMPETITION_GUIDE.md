# Cintana AI Challenge — Submission Guide

## What we're submitting

**SIGNAL EDU** — Evidence-based capability profiles for students, built with AI.

---

## Submission checklist

### Code & repository

- [ ] GitHub repository is public (or submitted URL is accessible to judges)
- [ ] `README.md` explains the product, stack, and how to run it
- [ ] `LICENSE` file present (MIT)
- [ ] Code is clean — no debug logs, no commented-out blocks, no TODO comments
- [ ] `.gitignore` is complete — no secrets, no `node_modules`, no `.next/`
- [ ] Git history is clean (no accidentally committed secrets)

### Deployed demo

- [ ] Frontend URL accessible without login: `https://signal-edu-app.vercel.app`
- [ ] Backend health endpoint responding: `https://YOUR-RENDER-URL.onrender.com/health`
- [ ] GitHub OAuth sign-in works end-to-end
- [ ] Analysis pipeline runs and completes
- [ ] Public profile `signal-edu.vercel.app/profile/[username]` accessible to anyone

### AI component

- [ ] Anthropic Claude is used for capability scoring (Sonnet) and recommendations (Haiku)
- [ ] AI output is structured and cited — not free-text hallucination
- [ ] Anti-hallucination guard documented and enforced in code
- [ ] Model choices are documented (see `ARCHITECTURE.md`)

### Product quality

- [ ] Mobile-responsive (test on 375px width)
- [ ] Dark mode works
- [ ] Error states handled (bad OAuth, analysis failure, empty profile)
- [ ] Loading states shown during analysis pipeline
- [ ] Empty state shown before first analysis run

### Documentation

- [ ] `docs/SETUP.md` — local development
- [ ] `docs/DEPLOYMENT.md` — production deployment
- [ ] `docs/ARCHITECTURE.md` — system design
- [ ] `docs/DEMO_GUIDE.md` — demo walkthrough
- [ ] `docs/TROUBLESHOOTING.md` — common issues

---

## Competition narrative

### Problem

University transcripts and resumes are poor proxies for actual engineering capability. A student who built a distributed system over two years looks identical on paper to one who hasn't written code outside of coursework. Institutions and employers have no structured, credible signal to differentiate them.

### Solution

SIGNAL analyzes a student's public GitHub activity and produces a structured capability profile across three dimensions: Technical Execution, Project Complexity, and Conceptual Quality. Every score is backed by a specific, citable repository artifact — no hallucinated claims.

### How AI makes this possible

Without AI, evaluating code quality and engineering judgment at scale is intractable. SIGNAL uses:
- **Claude Sonnet** to evaluate code architecture, design decisions, and engineering judgment in specific repository artifacts — tasks that require reading code with comprehension
- **Claude Haiku** to generate actionable, personalized recommendations based on the scored profile and target role gap

The anti-hallucination guard ensures the AI scoring layer is anchored to objective metrics — it can interpret and amplify what it observes, but cannot fabricate.

### Why this matters for Cintana

Cintana's mission connects students from underserved institutions to global opportunities. SIGNAL gives those students a credential that speaks for itself — one that a student at a top-ranked institution with an identical GPA cannot fabricate. The profile is built from real work, not reputation.

---

## Judging criteria mapping

| Criterion | How SIGNAL addresses it |
|---|---|
| **AI usage** | Claude Sonnet for scoring, Claude Haiku for recommendations; structured prompts with evidence citation |
| **Real-world impact** | Solves the talent signal problem for underrepresented students |
| **Technical execution** | Full-stack: Next.js + FastAPI + Supabase; RLS security; PKCE OAuth; ISR public profiles |
| **Product quality** | End-to-end user flow, error handling, mobile-responsive, dark mode |
| **Innovation** | Anti-hallucination scoring cap; evidence-backed profiles; public shareable URL |
| **Scalability** | Stateless FastAPI; Supabase Postgres with connection pooling; Vercel edge CDN |

---

## Live demo URL

`https://signal-edu-app.vercel.app`

Public profile example (no login required):
`https://signal-edu-app.vercel.app/profile/[your-github-username]`
