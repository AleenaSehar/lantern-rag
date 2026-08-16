import asyncio
from pathlib import Path


class LocalFileStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    async def save(self, document_id: str, suffix: str, content: bytes) -> str:
        return await asyncio.to_thread(self._save, document_id, suffix, content)

    def _save(self, document_id: str, suffix: str, content: bytes) -> str:
        self._root.mkdir(parents=True, exist_ok=True)
        destination = self._root / f"{document_id}{suffix.lower()}"
        temporary = destination.with_suffix(f"{destination.suffix}.tmp")
        temporary.write_bytes(content)
        temporary.replace(destination)
        return str(destination)

    async def delete(self, path: str | None) -> None:
        if path:
            await asyncio.to_thread(Path(path).unlink, missing_ok=True)

