import asyncio
from functools import cached_property

from sentence_transformers import SentenceTransformer


class LocalEmbeddingService:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    @cached_property
    def model(self) -> SentenceTransformer:
        # Lazy loading keeps health checks and API startup independent of model download time.
        return SentenceTransformer(self._model_name)

    def count_tokens(self, text: str) -> int:
        return len(self.model.tokenizer.encode(text, add_special_tokens=False))

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = await asyncio.to_thread(
            self.model.encode,
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

