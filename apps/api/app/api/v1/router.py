from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    cost_centers,
    dashboard,
    documents,
    health,
    invoices,
    suppliers,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(cost_centers.router, prefix="/cost-centers", tags=["cost-centers"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
