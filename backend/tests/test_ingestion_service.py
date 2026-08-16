from datetime import datetime, timezone

import pytest

from groundwork_api.domain.documents import Document, DocumentStatus
from groundwork_api.ingestion.service import IngestionService


class FakeDocuments:
    def __init__(self, existing: Document | None = None, create_success: bool = True) -> None:
        self.existing = existing
        self.create_success = create_success
        self.created: Document | None = None
        self.chunks = []
        self.failed: tuple[str, str] | None = None

    async def ensure_indexes(self) -> None:
        pass

    async def find_by_hash(self, _digest: str) -> Document | None:
        return self.existing

    async def create(self, document: Document, _path: str) -> bool:
        self.created = document
        return self.create_success

    async def replace_failed(self, document: Document, _path: str) -> None:
        self.created = document

    async def save_chunks(self, chunks: list) -> None:
        self.chunks = chunks

    async def mark_ready(self, document_id: str, chunk_count: int) -> Document:
        source = self.created
        assert source is not None
        return Document(
            **{
                **source.__dict__,
                "id": document_id,
                "status": DocumentStatus.READY,
                "chunk_count": chunk_count,
            }
        )

    async def delete_chunks(self, _document_id: str) -> None:
        self.chunks = []

    async def mark_failed(self, document_id: str, error: str) -> None:
        self.failed = (document_id, error)


class FakeVectors:
    def __init__(self) -> None:
        self.saved = []
        self.deleted: str | None = None

    async def ensure_collection(self) -> None:
        pass

    async def save(self, chunks: list, vectors: list, _filename: str) -> None:
        self.saved = list(zip(chunks, vectors, strict=True))

    async def delete_document(self, document_id: str) -> None:
        self.deleted = document_id


class FakeEmbeddings:
    def count_tokens(self, text: str) -> int:
        return len(text.split())

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]


class FailingEmbeddings(FakeEmbeddings):
    async def embed(self, _texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding failed")


class FakeStorage:
    def __init__(self) -> None:
        self.deleted: str | None = None

    async def save(self, document_id: str, suffix: str, _content: bytes) -> str:
        return f"data/{document_id}{suffix}"

    async def delete(self, path: str | None) -> None:
        self.deleted = path


def build_service(documents: FakeDocuments, embeddings: FakeEmbeddings):
    vectors = FakeVectors()
    storage = FakeStorage()
    service = IngestionService(documents, vectors, embeddings, storage, 500, 75)
    return service, vectors, storage


async def test_duplicate_ready_document_skips_pipeline() -> None:
    existing = Document(
        id="existing",
        filename="original.txt",
        content_type="text/plain",
        size_bytes=13,
        sha256="hash",
        status=DocumentStatus.READY,
        chunk_count=1,
        created_at=datetime.now(timezone.utc),
    )
    documents = FakeDocuments(existing)
    service, vectors, _storage = build_service(documents, FakeEmbeddings())

    document, duplicate = await service.ingest("copy.txt", "text/plain", b"same contents")

    assert document is existing
    assert duplicate is True
    assert vectors.saved == []


async def test_ingestion_persists_chunks_and_vectors() -> None:
    documents = FakeDocuments()
    service, vectors, _storage = build_service(documents, FakeEmbeddings())

    document, duplicate = await service.ingest(
        "evidence.txt", "text/plain", b"Grounded answers cite their evidence."
    )

    assert duplicate is False
    assert document.status is DocumentStatus.READY
    assert document.chunk_count == 1
    assert len(documents.chunks) == 1
    assert len(vectors.saved) == 1


async def test_concurrent_duplicate_discards_its_temporary_file() -> None:
    concurrent = Document(
        id="concurrent",
        filename="first.txt",
        content_type="text/plain",
        size_bytes=12,
        sha256="hash",
        status=DocumentStatus.PROCESSING,
        chunk_count=0,
        created_at=datetime.now(timezone.utc),
    )
    documents = FakeDocuments(create_success=False)
    calls = 0

    async def find_after_insert(_digest: str) -> Document | None:
        nonlocal calls
        calls += 1
        return None if calls == 1 else concurrent

    documents.find_by_hash = find_after_insert
    service, vectors, storage = build_service(documents, FakeEmbeddings())

    document, duplicate = await service.ingest("second.txt", "text/plain", b"same content")

    assert document is concurrent
    assert duplicate is True
    assert storage.deleted is not None
    assert vectors.saved == []


async def test_failure_cleans_partial_state_and_marks_document_failed() -> None:
    documents = FakeDocuments()
    service, vectors, storage = build_service(documents, FailingEmbeddings())

    with pytest.raises(RuntimeError, match="embedding failed"):
        await service.ingest("bad.txt", "text/plain", b"Some valid source text.")

    assert documents.failed is not None
    assert vectors.deleted == documents.failed[0]
    assert storage.deleted is not None
