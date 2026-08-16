from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from groundwork_api.domain.documents import Chunk
from groundwork_api.main import app
from groundwork_api.retrieval.service import RetrievalResult


class FakeRetrievalService:
    async def search(self, query: str, top_k: int, document_ids: list[str] | None):
        assert query == "What supports the answer?"
        assert top_k == 3
        assert document_ids == ["doc-1"]
        chunk = Chunk(
            id="chunk-1",
            document_id="doc-1",
            index=2,
            text="The source supports this answer.",
            page_number=4,
            char_start=20,
            char_end=52,
            token_count=6,
        )
        return [RetrievalResult(chunk=chunk, score=0.87, filename="source.pdf")]


async def test_search_returns_structured_chunk_provenance() -> None:
    app.state.retrieval_service = FakeRetrievalService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "What supports the answer?",
                "top_k": 3,
                "document_ids": ["doc-1"],
            },
        )

    assert response.status_code == 200
    assert response.json()["results"][0] == {
        "chunk_id": "chunk-1",
        "document_id": "doc-1",
        "filename": "source.pdf",
        "chunk_index": 2,
        "text": "The source supports this answer.",
        "score": 0.87,
        "page_number": 4,
        "char_start": 20,
        "char_end": 52,
        "token_count": 6,
    }


async def test_search_validates_blank_query_and_top_k() -> None:
    app.state.retrieval_service = SimpleNamespace()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/retrieval/search", json={"query": "   ", "top_k": 21}
        )

    assert response.status_code == 422

