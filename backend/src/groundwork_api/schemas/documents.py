from datetime import datetime

from pydantic import BaseModel, ConfigDict

from groundwork_api.domain.documents import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    chunk_count: int
    created_at: datetime
    error: str | None = None
    duplicate: bool = False


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]

