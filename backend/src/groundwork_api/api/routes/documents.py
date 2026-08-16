from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from groundwork_api.ingestion.extraction import ExtractionError
from groundwork_api.schemas.documents import DocumentListResponse, DocumentResponse

router = APIRouter(prefix="/documents")
_ALLOWED_SUFFIXES = {".pdf", ".txt"}


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request, file: Annotated[UploadFile, File()]
) -> DocumentResponse:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and TXT documents are supported",
        )

    settings = request.app.state.settings
    content = await file.read(settings.max_upload_bytes + 1)
    await file.close()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="File is empty"
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes}-byte limit",
        )
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File does not contain a valid PDF signature",
        )

    content_type = "application/pdf" if suffix == ".pdf" else "text/plain"
    try:
        document, duplicate = await request.app.state.ingestion_service.ingest(
            filename, content_type, content
        )
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document ingestion failed",
        ) from exc

    if duplicate:
        return DocumentResponse.model_validate(document).model_copy(update={"duplicate": True})
    return DocumentResponse.model_validate(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(request: Request) -> DocumentListResponse:
    documents = await request.app.state.document_repository.list()
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(document) for document in documents]
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, request: Request) -> DocumentResponse:
    document = await request.app.state.document_repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.model_validate(document)
