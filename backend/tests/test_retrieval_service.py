from groundwork_api.domain.documents import Chunk
from groundwork_api.domain.retrieval import VectorMatch
from groundwork_api.retrieval.service import RetrievalService


def make_chunk(chunk_id: str, index: int) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id="document-1",
        index=index,
        text=f"Text for {chunk_id}",
        page_number=None,
        char_start=index * 10,
        char_end=index * 10 + 10,
        token_count=3,
    )


class FakeEmbeddings:
    def __init__(self) -> None:
        self.query: str | None = None

    async def embed_query(self, query: str) -> list[float]:
        self.query = query
        return [0.1, 0.2]


class FakeVectors:
    def __init__(self) -> None:
        self.filters: list[str] | None = None
        self.limit: int | None = None
        self.ensured = False

    async def ensure_collection(self) -> None:
        self.ensured = True

    async def search(
        self, _vector: list[float], limit: int, document_ids: list[str] | None
    ) -> list[VectorMatch]:
        self.limit = limit
        self.filters = document_ids
        return [
            VectorMatch(chunk_id="chunk-b", score=0.92, filename="source.txt"),
            VectorMatch(chunk_id="chunk-a", score=0.81, filename="source.txt"),
        ]


class FakeDocuments:
    def __init__(self, include_all: bool = True) -> None:
        self.include_all = include_all

    async def get_chunks(self, _chunk_ids: list[str]) -> dict[str, Chunk]:
        chunks = {"chunk-b": make_chunk("chunk-b", 1)}
        if self.include_all:
            chunks["chunk-a"] = make_chunk("chunk-a", 0)
        return chunks


async def test_search_preserves_vector_ranking_and_filters() -> None:
    embeddings = FakeEmbeddings()
    vectors = FakeVectors()
    service = RetrievalService(FakeDocuments(), vectors, embeddings)

    results = await service.search("Where is the evidence?", 5, ["document-1"])

    assert embeddings.query == "Where is the evidence?"
    assert vectors.ensured is True
    assert vectors.limit == 5
    assert vectors.filters == ["document-1"]
    assert [result.chunk.id for result in results] == ["chunk-b", "chunk-a"]
    assert [result.score for result in results] == [0.92, 0.81]


async def test_search_rejects_dangling_vector_reference() -> None:
    service = RetrievalService(FakeDocuments(include_all=False), FakeVectors(), FakeEmbeddings())

    try:
        await service.search("query")
    except RuntimeError as exc:
        assert "chunk-a" in str(exc)
    else:
        raise AssertionError("Expected a missing MongoDB chunk to fail retrieval")

