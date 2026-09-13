"""Shared API schemas: error envelope and stats."""
from __future__ import annotations

from pydantic import BaseModel


class ErrorEnvelope(BaseModel):
    """Consistent error shape for every non-2xx response."""

    error: str  # stable machine code, e.g. CONTRACT_NOT_FOUND
    message: str
    request_id: str | None = None


class RiskDistribution(BaseModel):
    LOW: int = 0
    MEDIUM: int = 0
    HIGH: int = 0


class StatsResponse(BaseModel):
    contracts_total: int
    completed_analyses: int
    failed_analyses: int
    risk_distribution: RiskDistribution
    avg_processing_ms: float | None = None
    clauses_detected_total: int = 0
