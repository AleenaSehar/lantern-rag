from __future__ import annotations

from datetime import datetime

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from groundwork_api.domain.documents import Chunk, Document, DocumentStatus


class DocumentRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._documents = database.documents
        self._chunks = database.chunks

    async def ensure_indexes(self) -> None:
        await self._documents.create_index("sha256", unique=True)
        await self._documents.create_index([("created_at", -1)])
        await self._chunks.create_index([("document_id", 1), ("index", 1)], unique=True)

    async def find_by_hash(self, sha256: str) -> Document | None:
        record = await self._documents.find_one({"sha256": sha256})
        return self._to_document(record) if record else None

    async def get(self, document_id: str) -> Document | None:
        record = await self._documents.find_one({"_id": document_id})
        return self._to_document(record) if record else None

    async def list(self, limit: int = 100) -> list[Document]:
        cursor = self._documents.find().sort("created_at", -1).limit(limit)
        return [self._to_document(item) async for item in cursor]

    async def create(self, document: Document, storage_path: str) -> bool:
        try:
            await self._documents.insert_one(
                {
                    "_id": document.id,
                    "filename": document.filename,
                    "content_type": document.content_type,
                    "size_bytes": document.size_bytes,
                    "sha256": document.sha256,
                    "status": document.status.value,
                    "chunk_count": document.chunk_count,
                    "storage_path": storage_path,
                    "created_at": document.created_at,
                    "error": document.error,
                }
            )
        except DuplicateKeyError:
            return False
        return True

    async def replace_failed(self, document: Document, storage_path: str) -> None:
        await self._documents.update_one(
            {"_id": document.id},
            {
                "$set": {
                    "filename": document.filename,
                    "content_type": document.content_type,
                    "size_bytes": document.size_bytes,
                    "status": DocumentStatus.PROCESSING.value,
                    "chunk_count": 0,
                    "storage_path": storage_path,
                    "error": None,
                }
            },
        )

    async def save_chunks(self, chunks: list[Chunk]) -> None:
        if chunks:
            await self._chunks.insert_many(
                [
                    {
                        "_id": chunk.id,
                        "document_id": chunk.document_id,
                        "index": chunk.index,
                        "text": chunk.text,
                        "page_number": chunk.page_number,
                        "char_start": chunk.char_start,
                        "char_end": chunk.char_end,
                        "token_count": chunk.token_count,
                    }
                    for chunk in chunks
                ]
            )

    async def mark_ready(self, document_id: str, chunk_count: int) -> Document:
        await self._documents.update_one(
            {"_id": document_id},
            {"$set": {"status": DocumentStatus.READY.value, "chunk_count": chunk_count}},
        )
        document = await self.get(document_id)
        if document is None:
            raise RuntimeError("Document disappeared during ingestion")
        return document

    async def mark_failed(self, document_id: str, error: str) -> None:
        await self._documents.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "status": DocumentStatus.FAILED.value,
                    "chunk_count": 0,
                    "error": error,
                    "storage_path": None,
                }
            },
        )

    async def delete_chunks(self, document_id: str) -> None:
        await self._chunks.delete_many({"document_id": document_id})

    @staticmethod
    def _to_document(record: dict) -> Document:
        created_at: datetime = record["created_at"]
        return Document(
            id=record["_id"],
            filename=record["filename"],
            content_type=record["content_type"],
            size_bytes=record["size_bytes"],
            sha256=record["sha256"],
            status=DocumentStatus(record["status"]),
            chunk_count=record["chunk_count"],
            created_at=created_at,
            error=record.get("error"),
        )
