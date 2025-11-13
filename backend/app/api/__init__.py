from fastapi import APIRouter
from app.api.v1 import templates, combos, health

api_router = APIRouter()

# Include v1 routes
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(templates.router, prefix="/v1/templates", tags=["Templates"])
api_router.include_router(combos.router, prefix="/v1/combos", tags=["Combos"])

__all__ = ["api_router"]
