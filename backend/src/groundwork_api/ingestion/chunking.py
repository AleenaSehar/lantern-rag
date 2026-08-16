import re
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from groundwork_api.domain.documents import Chunk, ExtractedSection

_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n{2,}")


@dataclass(frozen=True)
class _Unit:
    text: str
    start: int
    end: int
    tokens: int


class TextChunker:
    def __init__(
        self,
        token_counter: Callable[[str], int],
        chunk_size: int = 500,
        overlap: int = 75,
    ) -> None:
        if overlap >= chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size")
        self._count = token_counter
        self._chunk_size = chunk_size
        self._overlap = overlap

    def split(self, document_id: str, sections: list[ExtractedSection]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section in sections:
            units = self._units(section.text)
            cursor = 0
            while cursor < len(units):
                end = cursor
                tokens = 0
                while end < len(units) and (
                    tokens + units[end].tokens <= self._chunk_size or end == cursor
                ):
                    tokens += units[end].tokens
                    end += 1
                selected = units[cursor:end]
                start_char, end_char = selected[0].start, selected[-1].end
                text = section.text[start_char:end_char].strip()
                chunks.append(
                    Chunk(
                        id=str(uuid4()),
                        document_id=document_id,
                        index=len(chunks),
                        text=text,
                        page_number=section.page_number,
                        char_start=start_char,
                        char_end=end_char,
                        token_count=self._count(text),
                    )
                )
                if end == len(units):
                    break
                overlap_tokens = 0
                next_cursor = end
                while next_cursor > cursor + 1 and overlap_tokens < self._overlap:
                    next_cursor -= 1
                    overlap_tokens += units[next_cursor].tokens
                cursor = next_cursor
        return chunks

    def _units(self, text: str) -> list[_Unit]:
        units: list[_Unit] = []
        start = 0
        for match in _BOUNDARY.finditer(text):
            end = match.start()
            self._append_unit(units, text, start, end)
            start = match.end()
        self._append_unit(units, text, start, len(text))
        return units

    def _append_unit(self, units: list[_Unit], source: str, start: int, end: int) -> None:
        while start < end and source[start].isspace():
            start += 1
        while end > start and source[end - 1].isspace():
            end -= 1
        if start == end:
            return
        text = source[start:end]
        tokens = self._count(text)
        if tokens <= self._chunk_size:
            units.append(_Unit(text=text, start=start, end=end, tokens=tokens))
            return
        # Long unbroken text is split by words so a single unit cannot defeat the target size.
        word_matches = list(re.finditer(r"\S+", text))
        batch_start = 0
        for index in range(1, len(word_matches)):
            candidate_start = start + word_matches[batch_start].start()
            candidate_end = start + word_matches[index].end()
            if self._count(source[candidate_start:candidate_end]) > self._chunk_size:
                previous_end = start + word_matches[index - 1].end()
                batch_text = source[candidate_start:previous_end]
                units.append(
                    _Unit(
                        text=batch_text,
                        start=candidate_start,
                        end=previous_end,
                        tokens=self._count(batch_text),
                    )
                )
                batch_start = index
        if batch_start < len(word_matches):
            tail_start = start + word_matches[batch_start].start()
            units.append(
                _Unit(
                    text=source[tail_start:end],
                    start=tail_start,
                    end=end,
                    tokens=self._count(source[tail_start:end]),
                )
            )
