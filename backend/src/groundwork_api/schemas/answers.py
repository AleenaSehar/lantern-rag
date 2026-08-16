from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnswerStatus(str, Enum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class GeneratedCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    quote: str


class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AnswerStatus
    answer: str
    citations: list[GeneratedCitation]

    @model_validator(mode="after")
    def validate_status_contract(self) -> "GeneratedAnswer":
        if self.status is AnswerStatus.ANSWERED and not self.citations:
            raise ValueError("Answered responses require at least one citation")
        if self.status is AnswerStatus.INSUFFICIENT_EVIDENCE and self.citations:
            raise ValueError("Insufficient-evidence responses cannot include citations")
        return self


class AnswerRequest(BaseModel):
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


class AnswerCitationResponse(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    chunk_index: int
    page_number: int | None
    char_start: int
    char_end: int
    quote: str


class AnswerResponse(BaseModel):
    query: str
    status: AnswerStatus
    answer: str
    citations: list[AnswerCitationResponse]
    retrieved_chunk_count: int
