"""Contract API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisSummary(BaseModel):
    """Compact analysis info embedded in contract detail/list views."""

    id: int
    status: str
    overall_risk_score: int | None = None
    overall_risk_level: str | None = None
    model_state: str | None = None
    model_version: str | None = None
    processing_ms: float | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class ContractResponse(BaseModel):
    """Contract metadata WITHOUT raw text (detail view adds analysis summary)."""

    id: str
    filename: str
    file_type: str
    status: str
    character_count: int | None = None
    page_count: int | None = None
    parser_warnings: list[str] = Field(default_factory=list)
    duplicate_of_id: str | None = None
    created_at: datetime | None = None
    latest_analysis: AnalysisSummary | None = None


class ContractListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ContractResponse]


class UploadResponse(ContractResponse):
    """Upload response: contract metadata (no auto-analysis)."""


class RawTextResponse(BaseModel):
    id: str
    filename: str
    character_count: int
    text: str


class DeletedResponse(BaseModel):
    deleted: bool
    id: str
