# INKSHIELD

**Evidence-first brand governance — verify before you publish.**

INKSHIELD checks marketing and product content against approved brand
knowledge (claims, terminology, product facts, guidelines, prohibited
phrases) and returns findings that always cite the exact knowledge record
behind them. A human reviewer then approves, rejects, edits, or escalates
each finding, and every scan and decision is recorded in an audit trail.

The principle: **AI makes a recommendation, evidence supports the
recommendation, a human owns the decision.**

## Live deployment (production)

| | |
| --- | --- |
| Frontend (Vercel) | <https://inkshield-rho.vercel.app> |
| API (Render) | <https://inkshield-api.onrender.com> |
| API health check | <https://inkshield-api.onrender.com/api/v1/health> |
| Interactive API docs | <https://inkshield-api.onrender.com/docs> |
| Repository | <https://github.com/Akash-Selvaraj-R/INKSHIELD> |

Submission materials (Round 2) live in [`docs/`](docs/) — see
[`docs/INKSHIELD-Round2-Submission.md`](docs/INKSHIELD-Round2-Submission.md)
and the matching PDF.

## Problem and target users

Brand, product-marketing, and compliance teams publish content faster than
they can verify it. Claims drift from the approved messaging, prohibited
phrases slip into ads, and when an incorrect claim ships nobody can say
which knowledge source or reviewer allowed it. INKSHIELD targets:

- **Content/marketing teams** who need a pre-publication check of claims,
  terminology, and facts.
- **Brand & compliance reviewers** who need evidence, not vibes: every
  finding cites a knowledge source and section.
- **Auditors/leads** who need an accountable record of what was scanned
  and who decided what.

## Key features

- **Evidence-first scanning** — a deterministic, knowledge-driven rule
  engine (`backend/app/rules/engine.py`) checks quantitative claims,
  prohibited absolutes, superlatives, and terminology. Every finding cites
  an actual seeded knowledge record (`source`, `section`, `text`); nothing
  is invented.
- **Selectable evidence sources** — scan against all five seeded knowledge
  sources (`claims`, `terms`, `guidelines`, `prohibited`, `facts`) or a
  subset. Unknown source ids are ignored, never fabricated.
- **Compliance score** — starts at 100 and drops by fixed severity weights
  (CRITICAL 15, HIGH 10, MEDIUM 5, LOW 2), clamped to [0, 100], plus a
  severity summary. Findings use sequential IDs (`INK-0042`, `INK-0043`, …)
  in reading order.
- **Human review workflow** — approve, reject, edit-and-approve, or
  escalate each finding. The API validates decisions (`EDITED` requires
  corrected text); deterministic scan data is never altered by a review,
  and updated state persists across reloads (`GET /api/v1/scans`).
- **Audit trail** — every successful scan and review decision appends an
  audit event with actor, action, and previous → new state. Failed
  requests (404/422) never produce events.
- **Honest error handling** — the typed frontend client surfaces real
  API/unreachable-backend errors in the UI and never updates the UI
  optimistically; a production build without `NEXT_PUBLIC_API_URL` fails
  with a clear configuration error instead of silently calling localhost.

## Architecture

```
Browser (Next.js 16, App Router)
   │  typed client: lib/api/client.ts  (NEXT_PUBLIC_API_URL)
   ▼
FastAPI (backend/, /api/v1)
   routes  →  services  →  rules / knowledge
   │            ├── scanner.py   scan pipeline + in-memory ScanStore
   │            ├── audit.py     in-memory append-only AuditLog
   │            └── knowledge.py seeded NOVA knowledge sources
   ▼
In-process memory (no database — see Known limitations)
```

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/v1/health` | Health and API version |
| POST | `/api/v1/scans` | Scan content → findings, summary, score (201) |
| GET | `/api/v1/scans` | Scans kept for the current server process |
| PATCH | `/api/v1/scans/{id}/findings/{id}/review` | Record a human decision (200) |
| GET | `/api/v1/audit-events` | Audit events, chronological |

Full API contract, request/response examples, and deployment notes:
[`backend/README.md`](backend/README.md).

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16.4.3 (App Router, Turbopack), React 19, TypeScript 5.7.3, Tailwind CSS 4, shadcn/base-ui, lucide-react, Vercel Analytics |
| Backend | Python 3.11+ (developed on 3.14), FastAPI, Pydantic v2, uvicorn |
| Tests | Vitest 5 (frontend, `pnpm test`), pytest + HTTPX `TestClient` (backend) |
| Deployment | Vercel (frontend), Render (backend, `render.yaml` blueprint) |
| Storage | In-process memory only — no database, no external services |

## Local setup

### Prerequisites

- Node.js 20.9+ with **pnpm** (`packageManager: pnpm@12.3.4`; Next.js
  requires `>=20.9.0`)
- Python 3.11+

### 1. Backend

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API on <http://127.0.0.1:8000>, docs at <http://127.0.0.1:8000/docs>.
No configuration required for local use.

### 2. Frontend

From the repository root:

```powershell
pnpm install
pnpm dev
```

Open <http://localhost:3000>. The API client falls back to
`http://127.0.0.1:8000` in development, so no environment file is needed.

## Tests and checks

Run from the repository root (no server required):

```powershell
pnpm test                          # Vitest — frontend
python -m pytest backend/tests -q  # pytest — backend (use backend\.venv\Scripts\python.exe if the venv is not active)
tsc --noEmit                       # TypeScript strict check (node_modules\.bin\tsc on Windows)
pnpm build                         # production build
```

Verified results on commit `22a05ef` (2026-10-29):

| Check | Result |
| --- | --- |
| `pnpm test` (Vitest) | **48/48 passed** across 4 test files |
| `python -m pytest backend/tests -q` | **52/52 passed** |
| `tsc --noEmit` | 0 errors (strict mode) |
| `pnpm build` | Build succeeded (Next.js 16.4.3, Turbopack) |
| `GET https://inkshield-api.onrender.com/api/v1/health` | HTTP 200 `{"status":"healthy",...}` |
| `GET https://inkshield-rho.vercel.app` | HTTP 200 |

Test coverage by area: API client (success, validation, unreachable
backend), rule engine (IDs, overlap suppression, all four rule families),
scan pipeline (scoring, determinism, no-fabricated-evidence invariant),
and API routes (scans 23, reviews 11, audit 12, health 2, CORS 4 — 52
total).

## Demo walkthrough (live)

1. **Open** <https://inkshield-rho.vercel.app> and click **SCAN CONTENT**
   (the landing page's four steps are CHECK → FIND EVIDENCE → EXPLAIN →
   APPROVE).
2. **Scan** on `/scan`: a demo draft is pre-filled (or paste your own),
   pick a content type and one or more evidence sources, then click
   **RUN INKSHIELD SCAN**.
3. **Inspect results**: compliance score `/100`, severity metrics, the
   submitted text with offending phrases highlighted, and one card per
   finding showing severity, submitted text, suggested correction,
   explanation, **evidence (source + section)**, and confidence. Selecting
   no evidence source or empty content shows a clear validation message —
   the scan is never faked.
4. **Review** a finding (card **Review** button or the drawer): choose
   **Approve**, **Reject**, **Edit & approve** (requires non-empty
   corrected text), or **Escalate**. The UI updates only after the API
   confirms; errors are shown in place.
5. **Verify persistence**: reload the page and check
   `GET /api/v1/scans` — the decision survives (until the backend
   restarts; see Known limitations).
6. **Audit trail** on `/audit`: each scan and decision appears with
   timestamp, actor, action, object, and state transition. Failed requests
   add no events.
7. **Error handling**: stop the backend (or unset `NEXT_PUBLIC_API_URL`
   in a production build) and the UI shows a precise error instead of
   fabricated findings.

Note: **Dashboard** KPIs, the **Knowledge Base** counts, and the
**Review Queue** items are illustrative demo data; **Scan History** and
**Settings** are labeled placeholders. The live end-to-end path is
Scan Content → results → review → Audit Trail.

## Known limitations

- **In-memory storage** — scans, review decisions, and audit events live
  in process memory only. Every restart, redeploy, or free-tier spin-down
  clears them; endpoints keep working, but history starts empty.
- **Cold starts** — the free Render backend may take a few seconds to wake
  up; the first request after idle can be slow (or time out and retry).
- **No authentication** — reviews are attributed to a generic "Reviewer"
  because no user accounts exist.
- **Deterministic scanner, not an LLM** — no RAG or external model calls;
  policy knowledge is the seeded demo knowledge base.
- **Duplicated scanner logic** — the Python scanner is an independent
  port of the TypeScript scanner; there is no cross-language sharing yet.
- **Partial UI wiring** — see the demo walkthrough note: some pages show
  static demo content, and `next.config.mjs` sets
  `typescript.ignoreBuildErrors` (run `tsc --noEmit` for type checking;
  there is no lint script).

## Environment variables

The frontend reads one environment variable (see `.env.example`):

| Variable | Purpose | Default |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Base URL of the FastAPI backend, no trailing slash | `http://127.0.0.1:8000` (development only) |

Local development works with no configuration. To override, copy
`.env.example` to `.env.local` and edit.

### Deploying the frontend to Vercel

The production build does **not** assume localhost. Before deploying, set
`NEXT_PUBLIC_API_URL` in Vercel → Project → Settings → Environment
Variables to the public origin of your deployed FastAPI backend:

```
NEXT_PUBLIC_API_URL=https://inkshield-api.onrender.com
```

Without it, scans fail with a clear configuration error instead of
silently calling a local server. On the backend side, allow the Vercel
origin via `INKSHIELD_CORS_ORIGINS` (see `backend/.env.example`).

The backend is deployed from the repository's `render.yaml` blueprint;
`backend/README.md` documents the exact service settings and the
dashboard-managed environment variables.

Never commit real secrets; `.env*` files are git-ignored.
