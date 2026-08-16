from groundwork_api.domain.documents import ExtractedSection
from groundwork_api.ingestion.chunking import TextChunker


def count_words(text: str) -> int:
    return len(text.split())


def test_chunks_preserve_page_and_character_provenance() -> None:
    text = "Alpha beta gamma. Delta epsilon zeta. Eta theta iota. Kappa lambda mu."
    chunks = TextChunker(count_words, chunk_size=6, overlap=3).split(
        "document-1", [ExtractedSection(text=text, page_number=4)]
    )

    assert len(chunks) == 3
    assert all(chunk.page_number == 4 for chunk in chunks)
    assert all(text[chunk.char_start : chunk.char_end].strip() == chunk.text for chunk in chunks)
    assert chunks[0].text == "Alpha beta gamma. Delta epsilon zeta."
    assert chunks[1].text.startswith("Delta epsilon zeta.")
    assert [chunk.index for chunk in chunks] == [0, 1, 2]


def test_chunks_never_cross_pdf_pages() -> None:
    sections = [
        ExtractedSection(text="First page evidence.", page_number=1),
        ExtractedSection(text="Second page evidence.", page_number=2),
    ]

    chunks = TextChunker(count_words, chunk_size=100, overlap=10).split("doc", sections)

    assert len(chunks) == 2
    assert [chunk.page_number for chunk in chunks] == [1, 2]


def test_long_unbroken_section_falls_back_to_word_groups() -> None:
    text = " ".join(f"word{index}" for index in range(13))

    chunks = TextChunker(count_words, chunk_size=5, overlap=1).split(
        "doc", [ExtractedSection(text=text, page_number=None)]
    )

    assert len(chunks) >= 3
    assert all(chunk.token_count <= 5 for chunk in chunks)

