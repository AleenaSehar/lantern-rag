from dataclasses import dataclass

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.server_api import ServerApi
from qdrant_client import AsyncQdrantClient

from groundwork_api.config import Settings


@dataclass
class Infrastructure:
    mongo_client: AsyncMongoClient
    mongo_database: AsyncDatabase
    qdrant_client: AsyncQdrantClient

    @classmethod
    def from_settings(cls, settings: Settings) -> "Infrastructure":
        mongo_client = AsyncMongoClient(
            settings.mongodb_uri,
            server_api=ServerApi("1"),
            tz_aware=True,
        )
        qdrant_client = AsyncQdrantClient(
            url=str(settings.qdrant_url),
            api_key=settings.qdrant_api_key,
        )
        return cls(
            mongo_client=mongo_client,
            mongo_database=mongo_client[settings.mongodb_database],
            qdrant_client=qdrant_client,
        )

    async def close(self) -> None:
        # One owner per event loop makes async client lifetimes predictable.
        await self.mongo_client.close()
        await self.qdrant_client.close()
