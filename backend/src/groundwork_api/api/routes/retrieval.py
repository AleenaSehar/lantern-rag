from fastapi import APIRouter, HTTPException, Request, status

from groundwork_api.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunkResponse,
)

router = APIRouter(prefix="/retrieval")


@router.post("/search", response_model=RetrievalResponse)
async def search(request_body: RetrievalRequest, request: Request) -> RetrievalResponse:
    try:
        results = await request.app.state.retrieval_service.search(
            query=request_body.query,
            top_k=request_body.top_k,
            document_ids=request_body.document_ids,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Retrieval failed",
        ) from exc
    return RetrievalResponse(
        query=request_body.query,
        results=[
            RetrievedChunkResponse(
                chunk_id=result.chunk.id,
                document_id=result.chunk.document_id,
                filename=result.filename,
                chunk_index=result.chunk.index,
                text=result.chunk.text,
                score=result.score,
                page_number=result.chunk.page_number,
                char_start=result.chunk.char_start,
                char_end=result.chunk.char_end,
                token_count=result.chunk.token_count,
            )
            for result in results
        ],
    )
