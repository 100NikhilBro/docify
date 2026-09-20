# Docify

**Understand Your Documents Better**

Repository: [github.com/100NikhilBro/docify](https://github.com/100NikhilBro/docify)

Docify is a multimodal retrieval-augmented generation (RAG) app for PDFs, Word docs, PowerPoint decks, and YouTube videos. Ask questions in plain English and get streamed answers with page or timestamp citations.

| Layer | Location | Role |
|---|---|---|
| Web UI | `web/` | Next.js marketing site + authenticated `/workspace` |
| API | `server/` | FastAPI: upload, chat streaming, file serving |
| Auth | Clerk | JWT on API (`Authorization: Bearer`); `/workspace` gated in the frontend |
| Vectors | Qdrant | Collection name `pdf_rag` (unchanged; product branding is Docify) |

---

## Architecture (as implemented)

```text
Browser (/workspace)
  → Clerk session; API calls send Bearer JWT
  → FastAPI
       POST /upload*     → background ingest (parse → chunk → embed → Qdrant + BM25 reload)
       POST /chat        → stream_question  ★ production Q&A path
       GET  /files/...   → tenant-scoped file / image serving
```

### Production HTTP `/chat` flow

`POST /chat` (auth required) → `app.qa.stream_ask.stream_question`:

1. **Rewrite** the user question (`rewrite_query_async`, optional session memory).
2. **Classify intent** (`classify_query`): `document_summary` | `aggregation` | `comparison` | chunk retrieval (default).
3. **Dispatch:**
   - Summary / aggregation / comparison → specialized handlers in `app.agent.handlers` (may read parsed JSON from disk and/or retrieve).
   - Default → **hybrid retrieve** (`retrieve_per_file_async`): dense Qdrant search + in-process BM25 → merge → Jina rerank (or vector/BM25 fallback) → parent-window expansion → per-file fair selection when multiple files are selected.
4. **Stream** the Gemini answer as raw tokens.

Response: `StreamingResponse` with `media_type="text/plain"` (plain token stream). **Not** Server-Sent Events (SSE).

### Experimental CLI (not production)

`server/main.py` → `ask_agentic_question` (planner + multi-query evidence gather).

- Marked **experimental** in module docstrings.
- **Not** wired to HTTP `/chat`.
- There is **no** reflection loop module; older docs that claimed one were incorrect.

Legacy helpers (offline/batch only): `app.qa.ask.ask_question`, `app.ingestion.process_pdfs_to_md`.

---

## Retrieval and chunking

**Chunking** (`app.ingestion.chunker`):

- Token windows via `tiktoken` (`cl100k_base`).
- Default ≈ **1000** tokens per chunk, **150** token overlap.
- Paragraph-aware splits; **not** embedding-based “semantic” chunking.

**Indexing** (upload job):

- Parse PDF / DOCX / PPTX / YouTube transcript → build chunks → embed (`gemini-embedding-2`) → store in Qdrant (`pdf_rag`, DOT + L2-normalized) → reload per-user BM25 from parsed JSON on disk.

**Query-time retrieval** (default chat path):

1. Dense vector search (Qdrant, filtered by `user_id` / selected files).
2. BM25 (`rank_bm25.BM25Okapi`) over in-memory per-user indexes built from disk JSON.
3. Merge by chunk id; Jina `jina-reranker-v2-base-multilingual` when `JINA_API_KEY` is set (otherwise score fallback).
4. Parent-window expansion (`window_size=1`) from parsed chunk JSON.
5. Multi-file fairness: minimum chunks per selected file, then fill remaining slots by score.

---

## Authentication

- Almost all API routes depend on `get_current_user`.
- **Required:** `Authorization: Bearer <token>`. Missing/invalid → **401**. There is **no** anonymous `default_tenant` fallback on the API.
- Production: Clerk JWT verified via `CLERK_JWKS_URL` (optional `CLERK_JWT_AUD`).
- Local/tests: mock tokens (`mock_test_token` / `mock_*`) only when `ALLOW_MOCK_AUTH=true` or `NODE_ENV` is `development` / `test` / `dev`. Mock auth is **blocked** in production.

Frontend: Clerk session; `getToken()` attached to upload/chat/file requests. `/workspace` is protected by Clerk middleware.

Optional **backend** Supabase (`SUPABASE_URL` / `SUPABASE_KEY`) stores chat sessions/messages when configured. The frontend does **not** use a Supabase client.

---

## Single-instance limitations

Designed for a **single API process** (or carefully coordinated local use):

| Component | Behavior | Limitation |
|---|---|---|
| BM25 | In-process memory, rebuilt from `data/.../parsed` JSON | Not shared across workers/replicas; each process must reload |
| Upload jobs | In-memory map + JSON under `data/jobs/` | Survives **same-machine** restart; not a distributed queue |
| Background work | FastAPI `BackgroundTasks` + some threads | Not multi-host safe |

Qdrant and (optional) Supabase can be remote; BM25 and job state cannot be treated as horizontally scaled without further work.

---

## Setup

### Backend (`server/.env`)

```env
NODE_ENV=development
GEMINI_API_KEY=
JINA_API_KEY=
LLAMA_CLOUD_API_KEY=
GROQ_API_KEY=
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
CLERK_JWKS_URL=
CLERK_JWT_AUD=
ALLOWED_ORIGINS=http://localhost:3000
ALLOW_MOCK_AUTH=true
```

### Frontend (`web/.env.local`)

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
NEXT_PUBLIC_BASE_API_URL=http://localhost:8000
```

### Run locally

```bash
# Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# API (port 8000 matches local frontend defaults)
cd server
pip install -r requirements.txt
uvicorn app.api.server:app --reload --host 0.0.0.0 --port 8000

# Web
cd web
npm install
npm run dev
```

The Docker image for the API listens on **7860** (see `server/Dockerfile`). Set `NEXT_PUBLIC_BASE_API_URL` to match your deployment.

---

## Tech stack

| Area | Choice |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind 4, Framer Motion, Clerk |
| Backend | FastAPI, Uvicorn |
| LLM | Gemini `gemini-3.1-flash-lite` |
| Embeddings | Gemini `gemini-embedding-2` |
| Vector DB | Qdrant collection `pdf_rag` (DOT + L2-normalized) |
| Lexical search | In-process BM25Okapi |
| Rerank | Jina (fallback to vector/BM25 blend if unavailable) |
| Memory (optional) | Supabase REST from the **backend** only |

---

## Tests

```bash
cd server
python -m unittest discover -s tests -v

# or explicitly:
python -m unittest tests.test_phase1_security tests.test_phase2_reliability -v
```

Frontend typecheck:

```bash
cd web
npx tsc --noEmit
```

---

## API surface (chat / upload — high level)

Unchanged contracts (do not rename for branding):

- `POST /chat` — body: `question`, optional `session_id`, `selected_files`; streams `text/plain`
- `GET|POST /chat/sessions`, `GET /chat/sessions/{id}/messages`
- Upload / job / file listing / delete under `/upload...`
- `GET /files/pdf`, image routes — path-sanitized, tenant-scoped

---

## Experimental CLI

```bash
cd server
python main.py
```

Uses planner + evidence gather for local research. Prefer HTTP `/chat` for anything user-facing.

---

## Repository

Source and issues: https://github.com/100NikhilBro/docify
