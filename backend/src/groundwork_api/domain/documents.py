from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class ExtractedSection:
    text: str
    page_number: int | None


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    index: int
    text: str
    page_number: int | None
    char_start: int
    char_end: int
    token_count: int


@dataclass(frozen=True)
class Document:
    id: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    chunk_count: int
    created_at: datetime
    error: str | None = None

