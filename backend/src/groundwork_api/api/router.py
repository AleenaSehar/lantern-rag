from fastapi import APIRouter

from groundwork_api.api.routes import answers, documents, health, retrieval

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(retrieval.router, tags=["retrieval"])
api_router.include_router(answers.router, tags=["answers"])
