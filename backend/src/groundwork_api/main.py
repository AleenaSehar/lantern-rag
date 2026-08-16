from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from groundwork_api import __version__
from groundwork_api.api.router import api_router
from groundwork_api.config import get_settings
from groundwork_api.database import Infrastructure


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.infrastructure = Infrastructure.from_settings(settings)
    yield
    await app.state.infrastructure.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="groundwork API",
        description="Grounded document Q&A with chunk-level citations.",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()

