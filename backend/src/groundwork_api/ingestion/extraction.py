import asyncio
import io
from pathlib import Path

from pypdf import PdfReader

from groundwork_api.domain.documents import ExtractedSection


class ExtractionError(ValueError):
    pass


async def extract_sections(filename: str, content: bytes) -> list[ExtractedSection]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return await asyncio.to_thread(_extract_text, content)
    if suffix == ".pdf":
        return await asyncio.to_thread(_extract_pdf, content)
    raise ExtractionError("Only PDF and TXT documents are supported")


def _extract_text(content: bytes) -> list[ExtractedSection]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ExtractionError("TXT documents must use UTF-8 encoding") from exc
    if not text.strip():
        raise ExtractionError("The document contains no extractable text")
    return [ExtractedSection(text=text, page_number=None)]


def _extract_pdf(content: bytes) -> list[ExtractedSection]:
    try:
        reader = PdfReader(io.BytesIO(content))
        sections = [
            ExtractedSection(text=page.extract_text() or "", page_number=index)
            for index, page in enumerate(reader.pages, start=1)
        ]
    except Exception as exc:
        raise ExtractionError("The PDF could not be read") from exc
    sections = [section for section in sections if section.text.strip()]
    if not sections:
        raise ExtractionError("The PDF contains no extractable text")
    return sections

