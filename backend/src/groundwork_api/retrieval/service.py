from dataclasses import dataclass

from groundwork_api.domain.documents import Chunk
from groundwork_api.ingestion.embeddings import LocalEmbeddingService
from groundwork_api.repositories.documents import DocumentRepository
from groundwork_api.repositories.vectors import VectorRepository


@dataclass(frozen=True)
class RetrievalResult:
    chunk: Chunk
    score: float
    filename: str


class RetrievalService:
    def __init__(
        self,
        documents: DocumentRepository,
        vectors: VectorRepository,
        embeddings: LocalEmbeddingService,
    ) -> None:
        self._documents = documents
        self._vectors = vectors
        self._embeddings = embeddings

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[RetrievalResult]:
        await self._vectors.ensure_collection()
        query_vector = await self._embeddings.embed_query(query)
        matches = await self._vectors.search(query_vector, top_k, document_ids)
        chunks = await self._documents.get_chunks([match.chunk_id for match in matches])
        missing = [match.chunk_id for match in matches if match.chunk_id not in chunks]
        if missing:
            raise RuntimeError(f"Vector index references missing chunks: {missing}")
        return [
            RetrievalResult(
                chunk=chunks[match.chunk_id],
                score=match.score,
                filename=match.filename,
            )
            for match in matches
        ]
