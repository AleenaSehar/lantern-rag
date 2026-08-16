import io

import pytest
from reportlab.pdfgen import canvas

from groundwork_api.ingestion.extraction import ExtractionError, extract_sections


async def test_extracts_utf8_text() -> None:
    sections = await extract_sections("notes.txt", b"First paragraph.\n\nSecond paragraph.")

    assert len(sections) == 1
    assert sections[0].page_number is None
    assert sections[0].text.startswith("First paragraph")


async def test_extracts_pdf_with_page_numbers() -> None:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "Evidence on page one")
    pdf.showPage()
    pdf.drawString(72, 720, "Evidence on page two")
    pdf.save()

    sections = await extract_sections("evidence.pdf", buffer.getvalue())

    assert [section.page_number for section in sections] == [1, 2]
    assert "page one" in sections[0].text
    assert "page two" in sections[1].text


async def test_rejects_non_utf8_text() -> None:
    with pytest.raises(ExtractionError, match="UTF-8"):
        await extract_sections("notes.txt", b"\xff\xfe\xfa")

