"""FastAPI dependencies: settings, service, cached analyzer, model health.

The ML model is a process-wide singleton, loaded LAZILY on first analysis and
reused for every request (never reloaded per request). Health checks read
configuration only - they never force a model load.
"""
from __future__ import annotations

import contextvars
from functools import lru_cache

from fastapi import Request

from ..core.config import Settings, load_settings
from ..core.exceptions import ContractIQError
from ..services.contract_analysis import ContractAnalysisService
from ..services.ml_adapter import MLAnalyzerAdapter

# request id is set by middleware and read by error handlers/loggers
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_service(request: Request) -> ContractAnalysisService:
    return request.app.state.service


@lru_cache(maxsize=1)
def _device_name() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def model_health(settings: Settings) -> dict:
    """Model availability WITHOUT loading transformers (cheap, config only)."""
    final_dir = settings.ml_model_config.parent.parent / "models" / "final"
    final_present = (final_dir / "config.json").exists()
    try:
        import json

        cfg = settings.ml_model_config.read_text(encoding="utf-8")
        model_id = json.loads(cfg).get("baseline_model", {}).get("model_id")
        version = json.loads(cfg).get("model_version")
    except Exception:
        model_id, version = None, None
    return {
        # the fine-tuned model is bundled; the baseline would download on demand
        "available": final_present or bool(model_id),
        "state": "fine_tuned" if final_present else "baseline_on_demand",
        "device": _device_name(),
        "final_model_present": final_present,
        "baseline_model_id": model_id,
        "model_version": version,
    }


def build_service(settings: Settings) -> ContractAnalysisService:
    """Factory used by app startup (tests may swap the analyzer afterwards)."""
    return ContractAnalysisService(
        settings=settings,
        analyzer=MLAnalyzerAdapter(settings.ml_model_config),
    )


__all__ = [
    "get_settings", "get_service", "model_health", "build_service",
    "request_id_var", "ContractIQError",
]
