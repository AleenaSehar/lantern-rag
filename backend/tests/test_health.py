from uuid import UUID

from httpx import ASGITransport, AsyncClient

from groundwork_api.main import app


async def test_health_reports_service_identity() -> None:
    # Lifespan is unnecessary here: liveness must not depend on infrastructure.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "lantern-api",
        "version": "0.1.0",
    }
    UUID(response.headers["X-Request-ID"])
