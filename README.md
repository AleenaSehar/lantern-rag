# groundwork

groundwork is a retrieval-augmented generation (RAG) document Q&A application. Users upload
PDF or text documents, ask questions, and receive answers grounded in the uploaded material.
Every answer will expose the exact source chunks used to produce it, making citation visibility
a core product behavior rather than an afterthought.

This is a portfolio project built to demonstrate an explainable, production-minded AI
engineering workflow from ingestion through retrieval, generation, and evaluation.

## Current status

**Phase 0 - Planning and scaffolding (implementation complete; awaiting commit approval)**

The architecture and initial application skeleton are complete and verified locally. The work
remains uncommitted pending review and explicit approval. Document ingestion has not started.

## Technology choices

groundwork uses the FARM stack: FastAPI, React, and MongoDB.

| Technology | Role | Why it is here |
| --- | --- | --- |
| FastAPI + Python | Async backend API | Python has the strongest AI/data ecosystem; FastAPI adds native async handling, generated OpenAPI documentation, and Pydantic-enforced contracts. |
| React + Vite + TypeScript | Browser application | React supports an interactive citation workflow, Vite keeps development fast, and TypeScript makes frontend/backend contracts easier to maintain. |
| Plain CSS | Interface styling | The focused application does not yet justify a utility framework; plain CSS keeps the rendered structure and design decisions easy to inspect. |
| MongoDB | Document metadata, chunk records, and chat history | Its document model fits evolving ingestion metadata and conversation records while preserving a clear source of truth outside the vector index. |
| Qdrant | Vector search | Self-hosting demonstrates vector-infrastructure knowledge and supports payload filtering, with a configuration-compatible path to Qdrant Cloud. |
| Sentence Transformers | Local embeddings | Local inference avoids per-document API cost and makes ingestion reproducible without a second hosted AI provider. |
| Groq | Answer generation | Its low inference latency suits interactive Q&A, and it builds on existing project experience without coupling embeddings to generation. |
| Docker Compose | Local infrastructure | One command provides repeatable MongoDB and Qdrant services without requiring cloud accounts. |

FastAPI was chosen over Express intentionally. The backend's central work is Python-native text
extraction, embedding, retrieval, evaluation, and LLM orchestration. Keeping that work in Python
avoids a cross-language AI layer, while FastAPI provides async I/O and Pydantic validation at the
HTTP boundary.

## Architecture

```text
Ingestion
PDF / TXT upload
      |
      v
validate -> extract text -> chunk -> embed -> Qdrant vectors
                                  |
                                  +-------> MongoDB metadata + chunk records

Question answering
question -> embed -> retrieve chunks -> generate grounded answer -> validate citations
                         |                              |
                         +------------------------------+
                           exact chunk IDs and excerpts
```

MongoDB is the source of truth for application records. Qdrant is a retrieval index whose
payloads retain stable IDs linking each vector to its MongoDB document and chunk records.

## Repository layout

```text
backend/        FastAPI application and backend tests
frontend/       React/Vite browser application
compose.yaml    Local MongoDB and Qdrant services
```

## Local setup

### Prerequisites

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js 20.19 or newer and npm
- Docker with Docker Compose

### 1. Configure the environment

```bash
cp .env.example .env
```

The defaults connect to the local Docker services. No API keys are needed in Phase 0.

### 2. Start MongoDB and Qdrant

```bash
docker compose up -d
```

MongoDB binds to `127.0.0.1:27017`. Qdrant's HTTP API and dashboard bind to
`127.0.0.1:6333`; its gRPC API binds to `127.0.0.1:6334`.

### 3. Run the API

```bash
cd backend
uv sync
uv run uvicorn groundwork_api.main:app --reload
```

The API is available at `http://localhost:8000`, with interactive documentation at
`http://localhost:8000/docs`.

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
```

`health` reports that the API process is alive. `ready` returns HTTP 200 only when MongoDB and
Qdrant are reachable, otherwise HTTP 503 with per-service status.

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Quality checks

```bash
cd backend
uv run ruff check .
uv run pytest

cd ../frontend
npm run lint
npm run build
```

## Delivery plan

### Phase 0 - Architecture and scaffolding

Establish repository structure, environment configuration, async FastAPI and MongoDB clients,
Qdrant connectivity, the React/Vite shell, local infrastructure, and baseline quality checks.

### Phase 1 - Ingestion

Add safe PDF/TXT upload and extraction, document lifecycle tracking, a justified chunking
strategy, local embeddings, MongoDB records, Qdrant indexing, and failure-path tests.

### Phase 2 - Retrieval and evaluation

Implement semantic retrieval with document filters and stable source metadata. Establish a
small labeled retrieval fixture before deciding whether hybrid search or reranking is warranted.

### Phase 3 - Grounded generation

Generate answers with Groq, define abstention behavior, validate structured answers and
citations with Pydantic, reject citations outside the retrieved context, and persist chat history.

### Phase 4 - Frontend workflow

Build document upload, ingestion progress, document selection, chat, and interactive citations
that reveal the exact source chunk.

### Phase 5 - Reliability and portfolio readiness

Complete end-to-end tests, error and loading states, logging, CI, security review, deployment
notes, fresh-clone documentation verification, demo data, and a recording script.

Every phase ends with a recap and explicit approval before the next phase begins.

## Development workflow

- `main` is the stable, portfolio-ready branch.
- `dev` is the integration branch for phase work.
- Work is presented as an uncommitted diff with validation results first.
- No commit is created without Aleena's explicit approval.
- Nothing is pushed to the remote implicitly.
- Each meaningful change updates this README in the same work session.

Because Git branches point to commits, the first approved scaffold commit will establish `main`.
The `dev` branch will then be created from that baseline for subsequent phases.

## Decisions log

- **2026-08-16 - FARM instead of MERN:** FastAPI keeps the AI pipeline in Python while providing
  async request handling and Pydantic-enforced HTTP schemas.
- **2026-08-16 - Self-hosted Qdrant:** local vector infrastructure has stronger portfolio value
  than hiding retrieval behind a managed service, while retaining a path to Qdrant Cloud.
- **2026-08-16 - Local MongoDB:** Docker Compose makes development reproducible without accounts;
  environment-based configuration leaves MongoDB Atlas available for deployment.
- **2026-08-16 - Local Sentence Transformers:** embeddings remain reproducible and free of API
  credentials; the specific model and dimensions will be selected before Phase 1 implementation.
- **2026-08-16 - Groq for generation:** Groq provides low-latency inference and uses existing
  project experience; the exact production model will be selected in Phase 3.
- **2026-08-16 - PyMongo Async API:** it is the native async MongoDB driver for a FastAPI service
  and avoids starting new work on the superseded Motor API.
- **2026-08-16 - Retrieval evaluation before optimization:** a labeled fixture will determine
  whether reranking or hybrid search adds measurable value.
- **2026-08-16 - Citation integrity is enforced in code:** generation may cite only chunk IDs in
  the retrieved context; citation grounding will not rely solely on prompt compliance.
- **2026-08-16 - Plain CSS:** the focused v1 interface does not justify framework overhead, and
  keeping styling direct makes the frontend easier to inspect.
- **2026-08-16 - Approval-gated Git history:** every commit is reviewed and explicitly approved
  before creation; `dev` integrates active work and `main` remains stable.

## License

No license has been selected yet.
