"""Health & model status routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.config import Settings
from ...api.deps import get_settings, model_health

router = APIRouter(tags=["health"])

APP_NAME = "ContractIQ"
APP_VERSION = "0.5.0"
APP_DESCRIPTION = "AI Contract Intelligence & Risk Analysis - AI-assisted analysis. Results should be reviewed by a qualified professional."


@router.get("/health", summary="Health check with database and model status")
def health(settings: Settings = Depends(get_settings)) -> dict:
    from ...db.database import get_engine, init_db

    database = "ok"
    try:
        engine = get_engine(settings.database_url)
        init_db(engine)
        engine.dispose()
    except Exception:
        database = "error"

    return {
        "status": "ok" if database == "ok" else "degraded",
        "app": APP_NAME,
        "version": APP_VERSION,
        "database": database,
        "model": model_health(settings),
    }
