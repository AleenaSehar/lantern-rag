import hashlib
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from groundwork_api.domain.documents import Document, DocumentStatus
from groundwork_api.ingestion.chunking import TextChunker
from groundwork_api.ingestion.embeddings import LocalEmbeddingService
from groundwork_api.ingestion.extraction import extract_sections
from groundwork_api.ingestion.storage import LocalFileStorage
from groundwork_api.repositories.documents import DocumentRepository
from groundwork_api.repositories.vectors import VectorRepository


class IngestionService:
    def __init__(
        self,
        documents: DocumentRepository,
        vectors: VectorRepository,
        embeddings: LocalEmbeddingService,
        storage: LocalFileStorage,
        chunk_size: int,
        overlap: int,
    ) -> None:
        self._documents = documents
        self._vectors = vectors
        self._embeddings = embeddings
        self._storage = storage
        self._chunk_size = chunk_size
        self._overlap = overlap

    async def ingest(
        self, filename: str, content_type: str, content: bytes
    ) -> tuple[Document, bool]:
        # Keep API startup independent of infrastructure; ingestion prepares its own stores.
        await self._documents.ensure_indexes()
        await self._vectors.ensure_collection()
        digest = hashlib.sha256(content).hexdigest()
        existing = await self._documents.find_by_hash(digest)
        if existing and existing.status is not DocumentStatus.FAILED:
            return existing, True

        document = existing or Document(
            id=str(uuid4()),
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            sha256=digest,
            status=DocumentStatus.PROCESSING,
            chunk_count=0,
            created_at=datetime.now(timezone.utc),
        )
        storage_path = await self._storage.save(document.id, Path(filename).suffix, content)
        if existing:
            await self._documents.replace_failed(document, storage_path)
        else:
            created = await self._documents.create(document, storage_path)
            if not created:
                await self._storage.delete(storage_path)
                concurrent = await self._documents.find_by_hash(digest)
                if concurrent is None:
                    raise RuntimeError("Duplicate upload race did not produce a document")
                return concurrent, True

        try:
            sections = await extract_sections(filename, content)
            chunker = TextChunker(
                self._embeddings.count_tokens,
                chunk_size=self._chunk_size,
                overlap=self._overlap,
            )
            chunks = chunker.split(document.id, sections)
            if not chunks:
                raise ValueError("The document produced no searchable chunks")
            vectors = await self._embeddings.embed([chunk.text for chunk in chunks])
            await self._documents.save_chunks(chunks)
            await self._vectors.save(chunks, vectors, filename)
            return await self._documents.mark_ready(document.id, len(chunks)), False
        except Exception as exc:
            await self._documents.delete_chunks(document.id)
            # Cleanup is best-effort so it never hides the ingestion error we need to diagnose.
            with suppress(Exception):
                await self._vectors.delete_document(document.id)
            await self._storage.delete(storage_path)
            await self._documents.mark_failed(document.id, str(exc))
            raise
