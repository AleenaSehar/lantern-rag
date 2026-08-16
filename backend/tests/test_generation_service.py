import json
from types import SimpleNamespace

import pytest

from groundwork_api.domain.documents import Chunk
from groundwork_api.generation.service import GroundedGenerationService, GroundingError
from groundwork_api.retrieval.service import RetrievalResult
from groundwork_api.schemas.answers import AnswerStatus


def retrieval_result() -> RetrievalResult:
    chunk = Chunk(
        id="chunk-1",
        document_id="doc-1",
        index=0,
        text="Battery storage preserves excess solar electricity for use after sunset.",
        page_number=2,
        char_start=10,
        char_end=79,
        token_count=11,
    )
    return RetrievalResult(chunk=chunk, score=0.91, filename="solar.pdf")


class FakeCompletions:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.request: dict | None = None

    async def create(self, **kwargs):
        self.request = kwargs
        message = SimpleNamespace(content=json.dumps(self.payload))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def service_with_payload(payload: dict) -> tuple[GroundedGenerationService, FakeCompletions]:
    service = GroundedGenerationService("test-key", "openai/gpt-oss-20b")
    completions = FakeCompletions(payload)
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return service, completions


async def test_generates_schema_constrained_cited_answer() -> None:
    service, completions = service_with_payload(
        {
            "status": "answered",
            "answer": "Battery storage makes excess solar power available after sunset.",
            "citations": [
                {
                    "chunk_id": "chunk-1",
                    "quote": "Battery storage preserves excess solar electricity",
                }
            ],
        }
    )

    answer = await service.generate("How is solar power used after dark?", [retrieval_result()])

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.citations[0].chunk_id == "chunk-1"
    assert completions.request["response_format"]["json_schema"]["strict"] is True


async def test_refuses_without_calling_groq_when_no_chunks_are_retrieved() -> None:
    service, completions = service_with_payload({})

    answer = await service.generate("What is not in the documents?", [])

    assert answer.status is AnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.citations == []
    assert completions.request is None


@pytest.mark.parametrize(
    ("citation", "message"),
    [
        ({"chunk_id": "invented", "quote": "fake"}, "unretrieved chunk"),
        ({"chunk_id": "chunk-1", "quote": "not in source"}, "not present"),
    ],
)
async def test_rejects_unsupported_citations(citation: dict, message: str) -> None:
    service, _ = service_with_payload(
        {"status": "answered", "answer": "Unsupported answer", "citations": [citation]}
    )

    with pytest.raises(GroundingError, match=message):
        await service.generate("question", [retrieval_result()])

