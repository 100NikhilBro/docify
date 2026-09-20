# Docify web

Next.js frontend for **Docify** — Understand Your Documents Better.

Repository: https://github.com/100NikhilBro/docify

## Run

```bash
npm install
npm run dev
```

## Env (`web/.env.local`)

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
NEXT_PUBLIC_BASE_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_BASE_API_URL` must point at the FastAPI server. Never commit `.env.local`.

## Behavior (as implemented)

- Marketing site at `/`; authenticated workspace at `/workspace` (Clerk).
- Workspace calls the API with `Authorization: Bearer <Clerk token>`.
- Chat uses `POST /chat` and reads a **`text/plain`** token stream (not SSE).
- Upload, sessions, and file preview hit the same API base URL.
- Light-only UI; no dark mode.

See the root [Readme.md](../Readme.md) for the production `/chat` pipeline, auth rules, retrieval/chunking, and single-instance BM25/job limits.
