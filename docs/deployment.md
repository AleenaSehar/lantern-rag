# Deployment notes

Lantern is currently designed for local, zero-cost operation. These notes describe a future
production topology; they are not instructions to create paid resources.

## Service topology

- Serve the built React files from a static host.
- Run the FastAPI application as a long-lived container with persistent storage for uploads.
- Use MongoDB and Qdrant endpoints supplied through environment variables.
- Keep `GROQ_API_KEY` only in the backend service's secret manager.
- Set `CORS_ORIGINS` to the deployed frontend origin rather than a wildcard.

Local Sentence Transformers avoid embedding API charges, but the backend needs enough memory for
PyTorch and `BAAI/bge-small-en-v1.5`. A free host with a small memory limit may not be suitable.
Benchmark memory and cold-start time before selecting a provider; do not silently replace local
embeddings with a paid API.

## Production gaps

Before public deployment, add authentication and per-user document isolation, move uploads to
durable object storage, rate-limit upload and answer endpoints, configure HTTPS, and define data
retention/deletion behavior. The current application is intentionally a single-user portfolio
deployment and must not be exposed as a multi-tenant service.

MongoDB and Qdrant compatibility identifiers retain their original `groundwork` values so the
product rename does not orphan existing local data. New deployments may override both names with
environment variables.
