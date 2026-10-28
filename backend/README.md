# INKSHIELD Backend (M3)

FastAPI foundation for INKSHIELD. It exposes a health endpoint and an
in-memory, deterministic content-scanning API driven by the seeded NOVA
demo knowledge base (a Python port of the M1/M2 TypeScript scanner).
There is no database, authentication, or frontend integration yet — those
belong to later milestones.

## Stack

- Python 3.11+ (developed and tested on Python 3.14)
- FastAPI + Pydantic (schemas, validation, routing)
- pytest + HTTPX (`TestClient` for API tests)
- uvicorn (local ASGI server)

## Project structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory (create_app) + uvicorn entry point
│   ├── api/
│   │   ├── router.py            # Versioned router assembly (/api/v1)
│   │   └── routes/
│   │       ├── health.py        # GET  /api/v1/health
│   │       └── scans.py         # POST /api/v1/scans, GET /api/v1/scans
│   ├── core/config.py           # Environment-driven settings (no secrets)
│   ├── schemas/scan.py          # Pydantic request/response models
│   ├── services/
│   │   ├── knowledge.py         # Seeded NOVA knowledge + source selection
│   │   └── scanner.py           # Scan pipeline, scoring, in-memory store
│   └── rules/engine.py          # Deterministic knowledge-driven rule engine
├── tests/
│   ├── conftest.py              # Fresh-app TestClient fixture
│   ├── test_health.py
│   └── test_scans.py
├── requirements.txt
├── .env.example                 # Placeholders only — never put secrets in the repo
└── README.md
```

Layering: `routes -> services -> rules/knowledge`, with `schemas` and
`core/config` shared at the edges. Policy information (limits, prohibited
phrases, approved terms) lives only in `services/knowledge.py`; the rule
engine never hardcodes NOVA-specific content.

## Setup (Windows)

From the repository root:

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks the activation script, either run it once with
`powershell -ExecutionPolicy Bypass -File .venv\Scripts\Activate.ps1` or
skip activation and call `.venv\Scripts\python.exe` / `.venv\Scripts\pip.exe`
directly. (cmd.exe users: `.venv\Scripts\activate.bat`.)

Optionally copy `.env.example` to `.env` and adjust values; the app uses
safe defaults when nothing is configured.

## Run the API

Inside `backend/` (with the virtual environment active):

```powershell
uvicorn app.main:app --reload
```

The API listens on <http://127.0.0.1:8000>. Interactive docs are at
<http://127.0.0.1:8000/docs>. Verify health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{ "status": "healthy", "service": "INKSHIELD API", "version": "v1" }
```

## Run the tests

From the repository root (no server required):

```powershell
python -m pytest backend/tests -q
```

Or from `backend/`: `python -m pytest tests -q`.

## API

| Method | Path                                          | Description                                            |
| ------ | --------------------------------------------- | ------------------------------------------------------ |
| GET    | `/api/v1/health`                              | Service health and API version                          |
| POST   | `/api/v1/scans`                               | Scan content; returns findings, summary, score (201)    |
| GET    | `/api/v1/scans`                               | Scans created during the current server process         |
| PATCH  | `/api/v1/scans/{scan_id}/findings/{finding_id}/review` | Record a human review decision for one finding (200) |

`POST /api/v1/scans` request:

```json
{
  "content": "NOVA is the fastest AI engine, delivering 50% faster inference.",
  "knowledge_sources": []
}
```

- `content` — required; empty or whitespace-only content is rejected with 422.
- `knowledge_sources` — optional list of source ids (`claims`, `terms`,
  `guidelines`, `prohibited`, `facts`). Empty/omitted means the complete
  seeded knowledge base; unknown ids are ignored, never fabricated. If no
  valid sources remain, the scan completes with no findings. The
  frontend's camelCase spelling `knowledgeSources` is accepted too (M4
  integration); extra fields such as `contentType` are ignored.

Response (abbreviated):

```json
{
  "id": "scan_1a2b3c4d5e6f",
  "status": "completed",
  "compliance_score": 45,
  "summary": { "total_findings": 2, "critical": 1, "high": 1, "medium": 0, "low": 0 },
  "findings": [
    {
      "id": "INK-0042",
      "category": "CLAIM",
      "severity": "CRITICAL",
      "status": "OPEN",
      "title": "Unsupported performance claim",
      "submitted_text": "50% faster inference",
      "explanation": "The submitted performance claim exceeds the maximum approved quantitative claim in the brand knowledge base (up to 30% faster).",
      "suggested_correction": "Up to 30% faster inference.",
      "confidence": 96,
      "evidence": [{ "source": "Product Claims", "section": "§4.2", "text": "Up to 30% faster inference." }],
      "review": { "required": true, "decision": null },
      "corrected_text": null
    }
  ],
  "content": "NOVA is the fastest AI engine, delivering 50% faster inference."
}
```

Findings are deterministic, use sequential IDs (`INK-0042`, `INK-0043`, …)
within each scan, and are returned in reading order. Evidence always cites
actual seeded knowledge records — nothing is invented. The compliance score
starts at 100 and drops by fixed severity weights (CRITICAL 15, HIGH 10,
MEDIUM 5, LOW 2), clamped to [0, 100].

## Human review (M5)

`PATCH /api/v1/scans/{scan_id}/findings/{finding_id}/review` records a
human-in-the-loop decision for a single finding:

```json
{ "decision": "EDITED", "correctedText": "Up to 30% faster inference." }
```

- `decision` — required; one of `APPROVED`, `REJECTED`, `EDITED`,
  `ESCALATED`. Any other value (or a missing/mistyped field) is rejected
  with 422.
- `correctedText` — optional except for `EDITED`, which requires a
  non-blank value (422 otherwise). The snake_case spelling
  `corrected_text` is accepted too; surrounding whitespace is stripped.

The response is the updated finding: `status` and `review.decision` both
become the decision, `EDITED` additionally stores `corrected_text` while
keeping `suggested_correction`. Deterministic scan data (title,
explanation, evidence, confidence, score) is never altered, unrelated
findings are never modified, and the updated state persists for
subsequent `GET /api/v1/scans` calls. Unknown scan or finding ids return
404 with a descriptive `detail`.

## CORS and frontend integration (M4)

The Next.js frontend calls this API through the typed client in
`lib/api/client.ts`. CORS origins are configured with
`INKSHIELD_CORS_ORIGINS` (comma-separated) and default to the local
Next.js dev origins (`http://localhost:3000`, `http://127.0.0.1:3000`).
For a deployed frontend (e.g. Vercel), set it to the real origin:

```powershell
$env:INKSHIELD_CORS_ORIGINS = "https://your-app.vercel.app"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The frontend needs the matching `NEXT_PUBLIC_API_URL` pointing at this
API (see the repository-root `.env.example` and `README.md`).

## Current limitations

- In-memory only: scans and review decisions live in process memory and
  reset on restart (no database).
- No RAG, external LLM calls, authentication, or audit-event
  architecture yet (audit trail is M6 scope).
- The Python scanner remains an independent port of the TypeScript
  scanner; no cross-language sharing exists yet.
