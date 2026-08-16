from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from groundwork_api.main import app


async def test_upload_rejects_unsupported_extension() -> None:
    app.state.settings = SimpleNamespace(max_upload_bytes=1024)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("notes.docx", b"content", "application/octet-stream")},
        )

    assert response.status_code == 415


async def test_upload_rejects_spoofed_pdf() -> None:
    app.state.settings = SimpleNamespace(max_upload_bytes=1024)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("notes.pdf", b"not a pdf", "application/pdf")},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "File does not contain a valid PDF signature"

