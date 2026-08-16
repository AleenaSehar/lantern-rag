import json

from groq import AsyncGroq

from groundwork_api.retrieval.service import RetrievalResult
from groundwork_api.schemas.answers import AnswerStatus, GeneratedAnswer

_SYSTEM_PROMPT = """You answer questions using only the supplied source chunks.

Rules:
1. Do not use outside knowledge, assumptions, or facts absent from the chunks.
2. If the chunks do not fully support an answer, return status "insufficient_evidence", a clear
   note explaining that the uploaded documents do not contain enough evidence, and no citations.
3. If supported, return status "answered" and cite every factual claim using chunk IDs from the
   supplied context.
4. Each citation quote must be an exact, contiguous excerpt from its cited chunk.
5. Never invent a chunk ID or quote.
"""


class GroundingError(ValueError):
    pass


class GroundedGenerationService:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    async def generate(self, query: str, results: list[RetrievalResult]) -> GeneratedAnswer:
        if not results:
            return GeneratedAnswer(
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                answer=(
                    "The uploaded documents do not contain enough evidence "
                    "to answer this question."
                ),
                citations=[],
            )

        context = "\n\n".join(
            (
                f"CHUNK ID: {result.chunk.id}\n"
                f"SOURCE: {result.filename}\n"
                f"PAGE: {result.chunk.page_number or 'N/A'}\n"
                f"TEXT:\n{result.chunk.text}"
            )
            for result in results
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"QUESTION:\n{query}\n\nSOURCE CHUNKS:\n{context}",
                },
            ],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "grounded_answer",
                    "strict": True,
                    "schema": GeneratedAnswer.model_json_schema(),
                },
            },
        )
        content = response.choices[0].message.content
        if content is None:
            raise GroundingError("Groq returned no answer content")
        generated = GeneratedAnswer.model_validate_json(content)
        self._validate_citations(generated, results)
        return generated

    @staticmethod
    def _validate_citations(answer: GeneratedAnswer, results: list[RetrievalResult]) -> None:
        chunks = {result.chunk.id: result.chunk.text for result in results}
        for citation in answer.citations:
            source_text = chunks.get(citation.chunk_id)
            if source_text is None:
                raise GroundingError(f"Answer cited an unretrieved chunk: {citation.chunk_id}")
            if citation.quote not in source_text:
                details = json.dumps({"chunk_id": citation.chunk_id, "quote": citation.quote})
                raise GroundingError(f"Citation quote is not present in its chunk: {details}")
