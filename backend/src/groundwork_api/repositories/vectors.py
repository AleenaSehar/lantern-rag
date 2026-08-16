from qdrant_client import AsyncQdrantClient, models

from groundwork_api.domain.documents import Chunk
from groundwork_api.domain.retrieval import VectorMatch


class VectorRepository:
    def __init__(self, client: AsyncQdrantClient, collection: str, dimension: int) -> None:
        self._client = client
        self._collection = collection
        self._dimension = dimension

    async def ensure_collection(self) -> None:
        if not await self._client.collection_exists(self._collection):
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=self._dimension,
                    distance=models.Distance.COSINE,
                ),
            )

    async def save(self, chunks: list[Chunk], vectors: list[list[float]], filename: str) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Every chunk must have exactly one embedding")
        await self._client.upsert(
            collection_name=self._collection,
            points=[
                models.PointStruct(
                    id=chunk.id,
                    vector=vector,
                    payload={
                        "document_id": chunk.document_id,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.index,
                        "filename": filename,
                        "page_number": chunk.page_number,
                        "char_start": chunk.char_start,
                        "char_end": chunk.char_end,
                    },
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
            wait=True,
        )

    async def delete_document(self, document_id: str) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )

    async def search(
        self,
        query_vector: list[float],
        limit: int,
        document_ids: list[str] | None = None,
    ) -> list[VectorMatch]:
        query_filter = None
        if document_ids:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchAny(any=document_ids),
                    )
                ]
            )
        response = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=["chunk_id", "filename"],
            with_vectors=False,
        )
        return [
            VectorMatch(
                chunk_id=str(point.payload["chunk_id"]),
                score=point.score,
                filename=str(point.payload["filename"]),
            )
            for point in response.points
        ]
