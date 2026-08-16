from pydantic import BaseModel, Field, field_validator


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    document_ids: list[str] | None = Field(default=None, max_length=50)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query must contain non-whitespace text")
        return value


class RetrievedChunkResponse(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float
    page_number: int | None
    char_start: int
    char_end: int
    token_count: int


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievedChunkResponse]

