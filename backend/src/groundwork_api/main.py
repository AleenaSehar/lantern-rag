import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from groundwork_api import __version__
from groundwork_api.api.router import api_router
from groundwork_api.config import get_settings
from groundwork_api.database import Infrastructure
from groundwork_api.generation.service import GroundedGenerationService
from groundwork_api.ingestion.embeddings import LocalEmbeddingService
from groundwork_api.ingestion.service import IngestionService
from groundwork_api.ingestion.storage import LocalFileStorage
from groundwork_api.repositories.documents import DocumentRepository
from groundwork_api.repositories.vectors import VectorRepository
from groundwork_api.retrieval.service import RetrievalService

logger = logging.getLogger("lantern.requests")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    app.state.infrastructure = Infrastructure.from_settings(settings)
    app.state.document_repository = DocumentRepository(app.state.infrastructure.mongo_database)
    app.state.vector_repository = VectorRepository(
        app.state.infrastructure.qdrant_client,
        settings.qdrant_collection,
        settings.embedding_dimension,
    )
    embeddings = LocalEmbeddingService(settings.embedding_model)
    app.state.ingestion_service = IngestionService(
        documents=app.state.document_repository,
        vectors=app.state.vector_repository,
        embeddings=embeddings,
        storage=LocalFileStorage(settings.upload_directory),
        chunk_size=settings.chunk_size_tokens,
        overlap=settings.chunk_overlap_tokens,
    )
    app.state.retrieval_service = RetrievalService(
        documents=app.state.document_repository,
        vectors=app.state.vector_repository,
        embeddings=embeddings,
    )
    app.state.generation_service = (
        GroundedGenerationService(settings.groq_api_key, settings.groq_model)
        if settings.groq_api_key
        else None
    )
    yield
    await app.state.infrastructure.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="lantern API",
        description="Grounded document Q&A with chunk-level citations.",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = str(uuid4())
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started_at) * 1_000
        response.headers["X-Request-ID"] = request_id
        # Paths are useful operational data; query strings and bodies may contain private text.
        logger.info(
            "request_complete method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
