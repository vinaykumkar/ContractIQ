"""Analysis API schemas."""
from __future__ import annotations

from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str | None = None
    version: str | None = None
    state: str | None = None
    device: str | None = None


class OverallRisk(BaseModel):
    score: int | None = None
    level: str | None = None


class Entities(BaseModel):
    """Key entities derived from clause extraction results."""

    parties: str | None = None
    agreement_date: str | None = None
    effective_date: str | None = None
    expiration_date: str | None = None
    governing_law: str | None = None
    document_name: str | None = None


class ClauseResultResponse(BaseModel):
    clause_type: str
    found: bool
    confidence: float | None = None
    text: str = ""
    start_char: int | None = None
    end_char: int | None = None
    risk_level: str | None = None
    risk_reason: str | None = None
    uncertain: bool = False


class RiskFindingResponse(BaseModel):
    rule_id: str
    clause_type: str | None = None
    severity: str | None = None
    weight: int | None = None
    reason: str | None = None
    evidence: str | None = None
    confidence: float | None = None
    uncertain: bool = False


class AnalysisResponse(BaseModel):
    """Full analysis payload for the intelligence view."""

    analysis_id: int
    contract_id: str
    status: str
    model: ModelInfo
    overall_risk: OverallRisk
    entities: Entities
    clauses: list[ClauseResultResponse]
    risk_findings: list[RiskFindingResponse]
    processing_ms: float | None = None
    disclaimer: str | None = None
    created_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class AnalyzeAcceptedResponse(BaseModel):
    """Returned by POST /analyze before/after completion (sync execution)."""

    analysis_id: int
    contract_id: str
    status: str
