# INKSHIELD

Evidence-first brand governance. The Next.js frontend (this repo root)
connects to the FastAPI backend in `backend/` (see `backend/README.md`
for API details, setup, and tests).

## Frontend environment variables

The frontend reads one environment variable (see `.env.example`):

| Variable             | Purpose                                                        | Default                                            |
| -------------------- | -------------------------------------------------------------- | -------------------------------------------------- |
| `NEXT_PUBLIC_API_URL` | Base URL of the FastAPI backend, no trailing slash            | `http://127.0.0.1:8000` (development only)         |

Local development works with no configuration: the API client falls back
to `http://127.0.0.1:8000` outside production builds. To override, copy
`.env.example` to `.env.local` and edit.

### Deploying the frontend to Vercel

The production build does **not** assume localhost. Before deploying,
set `NEXT_PUBLIC_API_URL` in Vercel → Project → Settings → Environment
Variables to the public origin of your deployed FastAPI backend, e.g.:

```
NEXT_PUBLIC_API_URL=https://inkshield-api.onrender.com
```

Without it, scans fail with a clear configuration error instead of
silently calling a local server. On the backend side, allow the Vercel
origin via `INKSHIELD_CORS_ORIGINS` (see `backend/.env.example`).

Never commit real secrets; `.env*` files are git-ignored.
