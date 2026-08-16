from fastapi import APIRouter

from groundwork_api.api.routes import documents, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, tags=["documents"])
