from fastapi import APIRouter, HTTPException, Request, status

from groundwork_api.generation.service import GroundingError
from groundwork_api.schemas.answers import (
    AnswerCitationResponse,
    AnswerRequest,
    AnswerResponse,
)

router = APIRouter(prefix="/answers")


@router.post("", response_model=AnswerResponse)
async def answer_question(request_body: AnswerRequest, request: Request) -> AnswerResponse:
    if request.app.state.generation_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured",
        )
    try:
        results = await request.app.state.retrieval_service.search(
            query=request_body.query,
            top_k=request_body.top_k,
            document_ids=request_body.document_ids,
        )
        generated = await request.app.state.generation_service.generate(
            request_body.query, results
        )
    except GroundingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The model returned an invalid grounded answer",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Answer generation failed",
        ) from exc

    result_by_id = {result.chunk.id: result for result in results}
    return AnswerResponse(
        query=request_body.query,
        status=generated.status,
        answer=generated.answer,
        citations=[
            AnswerCitationResponse(
                chunk_id=citation.chunk_id,
                document_id=result_by_id[citation.chunk_id].chunk.document_id,
                filename=result_by_id[citation.chunk_id].filename,
                chunk_index=result_by_id[citation.chunk_id].chunk.index,
                page_number=result_by_id[citation.chunk_id].chunk.page_number,
                char_start=result_by_id[citation.chunk_id].chunk.char_start,
                char_end=result_by_id[citation.chunk_id].chunk.char_end,
                quote=citation.quote,
            )
            for citation in generated.citations
        ],
        retrieved_chunk_count=len(results),
    )
