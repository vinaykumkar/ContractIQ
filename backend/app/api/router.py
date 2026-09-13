"""API router: everything under /api."""
from __future__ import annotations

from fastapi import APIRouter

from .routes import contracts, health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(contracts.router)
api_router.include_router(contracts.analyses_router)
api_router.include_router(contracts.stats_router)
