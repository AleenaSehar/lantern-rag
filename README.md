# lantern

lantern is a retrieval-augmented generation (RAG) document Q&A application. Users upload
PDF or text documents, ask questions, and receive answers grounded in the uploaded material.
Every answer will expose the exact source chunks used to produce it, making citation visibility
a core product behavior rather than an afterthought.

This is a portfolio project built to demonstrate an explainable, production-minded AI
engineering workflow from ingestion through retrieval, generation, and evaluation.

## Current status

**Version 1 complete - Portfolio-ready RAG workflow**

All five planned phases are merged into `main`. Lantern includes ingestion, evaluated retrieval,
strict grounded generation, interactive citations, frontend behavior tests, lockfile-driven CI,
privacy-conscious request logging, a repeatable demo, deployment notes, and an MIT License.

## Technology choices

lantern uses the FARM stack: FastAPI, React, and MongoDB.

| Technology | Role | Why it is here |
| --- | --- | --- |
| FastAPI + Python | Async backend API | Python has the strongest AI/data ecosystem; FastAPI adds native async handling, generated OpenAPI documentation, and Pydantic-enforced contracts. |
| React + Vite + TypeScript | Browser application | React supports an interactive citation workflow, Vite keeps development fast, and TypeScript makes frontend/backend contracts easier to maintain. |
| Plain CSS | Interface styling | The focused application does not yet justify a utility framework; plain CSS keeps the rendered structure and design decisions easy to inspect. |
| MongoDB | Document metadata and chunk records | Its document model fits evolving ingestion metadata while preserving a clear source of truth outside the vector index. Chat persistence is deferred until retention rules are defined. |
| Qdrant | Vector search | Self-hosting demonstrates vector-infrastructure knowledge and supports payload filtering, with a configuration-compatible path to Qdrant Cloud. |
| Sentence Transformers + BGE-small | Local embeddings | `BAAI/bge-small-en-v1.5` offers strong English retrieval at a practical 384 dimensions without a second hosted AI provider. |
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
payloads retain stable UUIDs linking each vector to its MongoDB document and chunk records.
Uploaded source files live under the ignored `data/uploads/` directory in development.

Short retrieval queries receive BGE's recommended English search instruction before embedding.
Qdrant ranks matching chunk UUIDs, then MongoDB supplies the authoritative chunk text without
changing that order.

## Repository layout

```text
backend/        FastAPI application and backend tests
frontend/       React/Vite browser application
demo/           Synthetic documents for a repeatable walkthrough
docs/           Demo script and deployment guidance
.github/        Pull-request and branch CI workflow
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

The defaults connect to the local Docker services. No API keys are needed through Phase 2.

For Phase 3, create a free Groq API key and set `GROQ_API_KEY` in `.env`. Stay on Groq's Free
plan without a payment method to avoid charges; exceeding free limits returns a rate-limit error.

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

The first document ingestion downloads `BAAI/bge-small-en-v1.5` from Hugging Face. Later runs
use the local model cache. PyTorch is locked to its official CPU build, avoiding unused CUDA
packages on development machines.

### 4. Ingest documents

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@/path/to/document.pdf"

curl http://localhost:8000/api/v1/documents
curl http://localhost:8000/api/v1/documents/{document_id}
```

Uploads support PDF and UTF-8 TXT files up to 10 MiB. The request completes after extraction,
chunking, embedding, and persistence. Re-uploading identical bytes returns the existing document
with `duplicate: true` instead of creating duplicate chunks or vectors.

### 5. Search documents

```bash
curl -X POST http://localhost:8000/api/v1/retrieval/search \
  -H "Content-Type: application/json" \
  -d '{"query":"How does the system work?","top_k":5}'
```

Add `document_ids` to limit search to selected documents. Results include similarity score,
chunk text, source filename, page, character offsets, and stable document/chunk IDs.

### 6. Generate a grounded answer

```bash
curl -X POST http://localhost:8000/api/v1/answers \
  -H "Content-Type: application/json" \
  -d '{"query":"How does the system work?","document_ids":["document-uuid"]}'
```

An answer has status `answered` with validated citations, or `insufficient_evidence` with a clear
refusal and no citations. Citation IDs must come from retrieval and quoted text must occur exactly
in the cited chunk.

> **Data boundary:** answer generation sends the retrieved source chunks to Groq. Use
> `document_ids` to control which documents can supply context. Ingestion, embedding, and
> retrieval remain local.

### 7. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The document panel lists indexed sources and controls which documents may supply evidence for a
question. Upload PDF or TXT files with the `+` button, select the relevant sources, and ask a
question in the conversation panel. Selecting a citation beneath an answer reveals the exact
source excerpt returned by the grounded-answer API.

Conversation messages are intentionally kept in browser memory during Phase 4 and are cleared by
a refresh. Persisted chat history requires a retention and privacy policy and is deferred until
that behavior can be designed explicitly.

### Quality checks

```bash
cd backend
uv run ruff check .
uv run pytest
uv run python scripts/evaluate_retrieval.py

cd ../frontend
npm run test
npm run lint
npm run build
```

GitHub Actions runs the same backend and frontend checks on pull requests and pushes to `main`
or `dev`. Tests do not call Groq and therefore do not require secrets or consume API quota.

Every API response includes a server-generated `X-Request-ID`. Request logs record only the HTTP
method, path, status, duration, and request ID; query strings and bodies are deliberately excluded
because they may contain private document content.

## Demo

The repository includes two synthetic documents so the core behavior can be demonstrated without
uploading private material. Follow the [two-minute demo script](docs/demo-script.md) to show
document-scoped retrieval, exact citation excerpts, and a deliberate refusal.

## Deployment and security

Lantern is locally runnable at no infrastructure cost. [Deployment notes](docs/deployment.md)
describe a future production topology and clearly identify the authentication, isolation,
storage, and rate-limiting work required before a public multi-user release.

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

Current synthetic baseline: `Recall@5 = 1.00`, `MRR = 1.00` across eight questions and six
documents. This is a regression/sanity benchmark, not a production-quality claim. Reranking and
hard score thresholds remain deferred until a larger or real-world corpus exposes a need.

### Phase 3 - Grounded generation

Generate answers with Groq, define abstention behavior, validate structured answers and
citations with Pydantic, and reject citations outside the retrieved context.

### Phase 4 - Frontend workflow

Build document upload, ingestion progress, document selection, chat, and interactive citations
that reveal the exact source chunk. The initial conversation is session-local; MongoDB chat
history remains deferred until retention and deletion behavior is defined.

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

Both branches are established on GitHub. Phase work begins on `dev`; approved stable milestones
can later be promoted to `main` through an explicit review step.

## Decisions log

- **2026-08-16 - FARM instead of MERN:** FastAPI keeps the AI pipeline in Python while providing
  async request handling and Pydantic-enforced HTTP schemas.
- **2026-08-16 - Self-hosted Qdrant:** local vector infrastructure has stronger portfolio value
  than hiding retrieval behind a managed service, while retaining a path to Qdrant Cloud.
- **2026-08-16 - Local MongoDB:** Docker Compose makes development reproducible without accounts;
  environment-based configuration leaves MongoDB Atlas available for deployment.
- **2026-08-16 - Local Sentence Transformers:** embeddings remain reproducible and free of API
  credentials; `BAAI/bge-small-en-v1.5` balances English retrieval quality, 384-dimensional
  storage, and CPU ingestion cost.
- **2026-08-16 - Structure-aware 500/75 chunking:** chunks target 500 model tokens with 75-token
  overlap, prefer paragraph/sentence boundaries, and never cross PDF pages so citations retain
  clear provenance.
- **2026-08-16 - Stable application UUIDs:** document and chunk IDs are generated outside either
  database and shared between MongoDB records and Qdrant payloads for machine-checkable citations.
- **2026-08-16 - SHA-256 idempotency:** identical file bytes resolve to the existing document,
  preventing duplicate embeddings even when the upload filename changes.
- **2026-08-16 - Local atomic file storage:** v1 stores ignored source files on disk via atomic
  replacement; the storage boundary can move to S3-compatible object storage at deployment time.
- **2026-08-16 - Synchronous v1 ingestion:** upload requests wait for indexing while durable
  processing/ready/failed states preserve observability without introducing a premature queue.
- **2026-08-16 - CPU-only PyTorch:** the lockfile uses PyTorch's official CPU wheel index to avoid
  pulling several gigabytes of unused CUDA dependencies for local embeddings.
- **2026-08-16 - Groq for generation:** Groq provides low-latency inference and uses existing
  project experience; the exact production model will be selected in Phase 3.
- **2026-08-16 - PyMongo Async API:** it is the native async MongoDB driver for a FastAPI service
  and avoids starting new work on the superseded Motor API.
- **2026-08-16 - Retrieval evaluation before optimization:** a labeled fixture will determine
  whether reranking or hybrid search adds measurable value.
- **2026-08-16 - Five-result dense retrieval baseline:** Qdrant cosine search returns five chunks
  by default, with optional document filtering and no uncalibrated hard score threshold.
- **2026-08-16 - BGE query instruction:** short questions receive the model's recommended English
  retrieval prefix; stored passages remain unprefixed.
- **2026-08-16 - No Phase 2 reranker:** the synthetic baseline placed every relevant chunk first,
  so a second model would add latency and complexity without demonstrated benefit.
- **2026-08-16 - Citation integrity is enforced in code:** generation may cite only chunk IDs in
  the retrieved context; citation grounding will not rely solely on prompt compliance.
- **2026-08-16 - Strict insufficient-evidence behavior:** when retrieved chunks do not support an
  answer, the API returns a clear refusal with no citations instead of inviting model guesswork.
- **2026-08-16 - GPT-OSS 20B structured output:** Groq's `openai/gpt-oss-20b` constrains responses
  to the Pydantic-derived JSON schema and is available within free-tier rate limits.
- **2026-08-16 - Exact quote validation:** application code verifies each cited ID was retrieved
  and each citation quote is a contiguous excerpt of that chunk before returning the answer.
- **2026-08-16 - Plain CSS:** the focused v1 interface does not justify framework overhead, and
  keeping styling direct makes the frontend easier to inspect.
- **2026-08-17 - Session-local conversation:** Phase 4 keeps chat in browser memory until
  retention, deletion, and multi-session behavior are designed together for MongoDB persistence.
- **2026-08-17 - Inline expandable citations:** source excerpts open beneath the answer so users
  can inspect evidence without losing their place in the conversation.
- **2026-08-17 - Lantern product name:** the user-facing project and package metadata were renamed
  while stable Python imports and data-store identifiers were retained to avoid needless data
  migration and code churn.
- **2026-08-17 - Deterministic CI:** frontend tests mock HTTP responses and backend tests mock the
  generation boundary, so pull-request checks use no Groq quota or infrastructure secrets.
- **2026-08-17 - Metadata-only request logging:** server-generated request IDs and timing support
  diagnosis without writing document content, questions, filenames, or credentials to logs.
- **2026-08-17 - Deployment documented, not purchased:** Phase 5 records the production topology
  and its security gaps without creating paid cloud resources.
- **2026-08-17 - MIT License:** the source remains copyrighted to Aleena Sehar while allowing
  reuse, modification, and distribution when the copyright and license notice are preserved.
- **2026-08-16 - Approval-gated Git history:** every commit is reviewed and explicitly approved
  before creation; `dev` integrates active work and `main` remains stable.

## License

Lantern is available under the [MIT License](LICENSE). Copyright remains with Aleena Sehar;
the license permits reuse and modification while providing the software without warranty.
