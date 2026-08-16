from dataclasses import dataclass


@dataclass(frozen=True)
class VectorMatch:
    chunk_id: str
    score: float
    filename: str

