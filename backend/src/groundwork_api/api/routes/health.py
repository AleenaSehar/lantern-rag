import asyncio

from fastapi import APIRouter, Request, Response, status

from groundwork_api import __version__
from groundwork_api.database import Infrastructure
from groundwork_api.schemas.health import DependencyStatus, HealthResponse, ReadinessResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report process liveness without depending on external services."""
    return HealthResponse(status="ok", service="lantern-api", version=__version__)


async def _mongo_status(infrastructure: Infrastructure) -> DependencyStatus:
    try:
        await infrastructure.mongo_database.command("ping")
        return DependencyStatus(status="up")
    except Exception as exc:  # The readiness response should describe dependency failures.
        return DependencyStatus(status="down", detail=type(exc).__name__)


async def _qdrant_status(infrastructure: Infrastructure) -> DependencyStatus:
    try:
        await infrastructure.qdrant_client.get_collections()
        return DependencyStatus(status="up")
    except Exception as exc:
        return DependencyStatus(status="down", detail=type(exc).__name__)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Report whether the API can reach every required persistence service."""
    infrastructure: Infrastructure = request.app.state.infrastructure
    mongo, qdrant = await asyncio.gather(
        _mongo_status(infrastructure),
        _qdrant_status(infrastructure),
    )
    dependencies = {"mongodb": mongo, "qdrant": qdrant}
    is_ready = all(item.status == "up" for item in dependencies.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        dependencies=dependencies,
    )
