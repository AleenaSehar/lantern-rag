from httpx import ASGITransport, AsyncClient

from groundwork_api.domain.documents import Chunk
from groundwork_api.main import app
from groundwork_api.retrieval.service import RetrievalResult
from groundwork_api.schemas.answers import AnswerStatus, GeneratedAnswer, GeneratedCitation


class FakeRetrievalService:
    async def search(self, query: str, top_k: int, document_ids: list[str] | None):
        assert query == "How is energy saved?"
        assert top_k == 5
        assert document_ids is None
        chunk = Chunk(
            id="chunk-1",
            document_id="doc-1",
            index=0,
            text="Batteries store excess energy.",
            page_number=None,
            char_start=0,
            char_end=30,
            token_count=5,
        )
        return [RetrievalResult(chunk=chunk, score=0.9, filename="energy.txt")]


class FakeGenerationService:
    async def generate(self, _query: str, _results: list[RetrievalResult]):
        return GeneratedAnswer(
            status=AnswerStatus.ANSWERED,
            answer="Batteries store it.",
            citations=[
                GeneratedCitation(chunk_id="chunk-1", quote="Batteries store excess energy.")
            ],
        )


async def test_answer_endpoint_returns_visible_citation_metadata() -> None:
    app.state.retrieval_service = FakeRetrievalService()
    app.state.generation_service = FakeGenerationService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/answers", json={"query": "How is energy saved?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["citations"][0]["filename"] == "energy.txt"
    assert body["citations"][0]["quote"] == "Batteries store excess energy."


async def test_answer_endpoint_requires_configured_groq_key() -> None:
    app.state.generation_service = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/answers", json={"query": "A question"})

    assert response.status_code == 503
    assert response.json()["detail"] == "GROQ_API_KEY is not configured"

