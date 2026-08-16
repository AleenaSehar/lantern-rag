from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from groundwork_api import __version__
from groundwork_api.api.router import api_router
from groundwork_api.config import get_settings
from groundwork_api.database import Infrastructure
from groundwork_api.ingestion.embeddings import LocalEmbeddingService
from groundwork_api.ingestion.service import IngestionService
from groundwork_api.ingestion.storage import LocalFileStorage
from groundwork_api.repositories.documents import DocumentRepository
from groundwork_api.repositories.vectors import VectorRepository
from groundwork_api.retrieval.service import RetrievalService


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
    yield
    await app.state.infrastructure.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="groundwork API",
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
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
