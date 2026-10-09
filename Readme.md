# Docify

### Understand Your Documents Better

Docify is a multimodal Retrieval-Augmented Generation (RAG) application that lets users ask questions about PDFs, Word documents, PowerPoint presentations, and YouTube videos. It combines hybrid retrieval and LLM-based generation to provide relevant answers with page or timestamp citations.

---

## Architecture

![Docify Architecture](https://github.com/user-attachments/assets/58a23bd4-6f9b-4afe-a603-27c4ac7d06e2)

### Indexing Pipeline

```text
PDF / DOCX / PPTX / YouTube
             ↓
      Content Extraction
             ↓
           Chunking
             ↓
     Embedding Generation
             ↓
       Qdrant Indexing
             ↓
      BM25 Index Reload
```

### Query Pipeline

```text
User Query
    ↓
Query Rewriting
    ↓
Intent Classification
    ↓
Specialized Handler OR Hybrid Retrieval
                              ↓
                    Dense Search + BM25
                              ↓
                      Merge Candidates
                              ↓
                           Reranking
                              ↓
                    Parent-Window Expansion
                              ↓
                       Relevant Context
                              ↓
                     Gemini Generation
                              ↓
                      Streamed Response
```

Specialized handlers support document summaries, aggregation, and comparisons. General questions use the hybrid retrieval pipeline.

---

## Features

- **Multimodal Document Processing** — Supports PDF, DOCX, PPTX, and YouTube transcripts.
- **Hybrid Retrieval** — Combines dense vector search with BM25 lexical search.
- **Query Understanding** — Rewrites questions and classifies intent for specialized handling.
- **Reranking** — Uses Jina reranking to improve candidate relevance, with a fallback scoring path.
- **Context Expansion** — Retrieves neighboring chunks to provide additional context.
- **Streaming Responses** — Streams generated answers to the client.
- **Source Citations** — Provides page or timestamp citations where supported.
- **Authentication & Isolation** — Uses Clerk JWT authentication and user-scoped retrieval and file access.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Animations | Framer Motion |
| Authentication | Clerk |
| Backend | FastAPI, Uvicorn |
| LLM | Gemini 3.1 Flash-Lite |
| Embeddings | Gemini Embedding 2 |
| Vector Database | Qdrant |
| Lexical Retrieval | BM25Okapi |
| Reranking | Jina Reranker v2 Multilingual |
| Optional Chat Persistence | Supabase REST |

---

## Getting Started

### Prerequisites

- Python and pip
- Node.js and npm
- Docker
- Gemini API key
- Clerk application credentials

### 1. Clone the Repository

```bash
git clone https://github.com/100NikhilBro/docify.git
cd docify
```

### 2. Start Qdrant

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  qdrant/qdrant
```

### 3. Configure Environment Variables

Create `server/.env`:

```env
NODE_ENV=development
GEMINI_API_KEY=
JINA_API_KEY=

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

CLERK_JWKS_URL=
CLERK_JWT_AUD=

SUPABASE_URL=
SUPABASE_KEY=

ALLOWED_ORIGINS=http://localhost:3000
ALLOW_MOCK_AUTH=true
```

Create `web/.env.local`:

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
NEXT_PUBLIC_BASE_API_URL=http://localhost:8000
```

Add the appropriate credentials for your environment. Mock authentication is for development/testing only and is blocked in production.

### 4. Run the Backend

```bash
cd server
pip install -r requirements.txt

uvicorn app.api.server:app \
  --reload \
  --host 0.0.0.0 \
  --port 8000
```

### 5. Run the Frontend

In a separate terminal:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000` to access the application.

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/chat` | Ask a question and receive a streamed response |
| GET | `/chat/sessions` | Retrieve chat sessions |
| POST | `/chat/sessions` | Create a chat session |
| GET | `/chat/sessions/{id}/messages` | Retrieve session messages |
| GET | `/files/...` | Access authorized files and images |

Upload, job-status, file-listing, and deletion operations are also available through the upload API routes.

The `/chat` endpoint streams plain text using FastAPI `StreamingResponse`; it does not currently use Server-Sent Events (SSE).

---

## Testing

**Backend**

```bash
cd server
python -m unittest discover -s tests -v
```

**Frontend**

```bash
cd web
npx tsc --noEmit
```

---

## Scalability Considerations

The current implementation has single-instance limitations:

- BM25 indexes are maintained in process memory.
- Upload job state uses in-memory data and local JSON files.
- Background ingestion uses FastAPI `BackgroundTasks` and threads.

Horizontal scaling requires coordinated shared state and a durable distributed job-processing design.

---

## Author

**Nikhil Gupta**

Built & Improved by **Nikhil Gupta**

[GitHub](https://github.com/100NikhilBro)
