"""SQLAlchemy persistence models.

Privacy: the full contract text is stored ONLY in Contract.raw_text, and only
when STORE_RAW_TEXT is enabled (needed for document evidence highlighting).
Analysis metadata and results are always stored. No secrets are ever persisted.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def _pk():
    """Portable 32-char hex primary key (TEXT/VARCHAR on every dialect).

    Deliberately a plain String everywhere: SQLite would coerce an INTEGER
    primary key and reject our uuid-hex ids.
    """
    return String(32)


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(_pk(), primary_key=True)
    filename = Column(String(255), nullable=False)          # sanitized display name
    original_filename = Column(String(255), nullable=True)  # as uploaded (traceability)
    file_type = Column(String(10), nullable=False)          # pdf | docx | txt
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    status = Column(String(20), nullable=False, default="UPLOADED")
    character_count = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    text_hash = Column(String(64), nullable=True, index=True)  # sha256 of normalized text
    parser_warnings = Column(Text, nullable=True)           # JSON list
    stored_path = Column(String(500), nullable=True)        # project-relative, if retained
    raw_text = Column(Text, nullable=True)                  # ONLY when STORE_RAW_TEXT=true
    duplicate_of_id = Column(_pk(), ForeignKey("contracts.id"), nullable=True)

    analyses = relationship(
        "Analysis", back_populates="contract", cascade="all, delete-orphan",
        order_by="Analysis.id.desc()",
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(_pk(), ForeignKey("contracts.id"), nullable=False, index=True)
    model_name = Column(String(255), nullable=True)
    model_version = Column(String(255), nullable=True)
    model_state = Column(String(50), nullable=True)         # fine_tuned | zero_shot_baseline
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_ms = Column(Float, nullable=True)
    overall_risk_score = Column(Integer, nullable=True)
    overall_risk_level = Column(String(10), nullable=True)
    status = Column(String(20), nullable=False, default="ANALYZING")  # ANALYZING/COMPLETED/FAILED
    error_message = Column(Text, nullable=True)
    disclaimer = Column(Text, nullable=True)

    contract = relationship("Contract", back_populates="analyses")
    clause_results = relationship(
        "ClauseResult", back_populates="analysis", cascade="all, delete-orphan",
        order_by="ClauseResult.id",
    )
    risk_findings = relationship(
        "RiskFinding", back_populates="analysis", cascade="all, delete-orphan",
        order_by="RiskFinding.id",
    )


class ClauseResult(Base):
    __tablename__ = "clause_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    clause_type = Column(String(100), nullable=False)
    found = Column(Integer, nullable=False, default=0)      # boolean as 0/1
    extracted_text = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    risk_level = Column(String(10), nullable=True)          # per-clause heuristic level
    risk_reason = Column(Text, nullable=True)
    uncertain = Column(Integer, nullable=True, default=0)   # low-confidence finding flag

    analysis = relationship("Analysis", back_populates="clause_results")


class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    rule_id = Column(String(100), nullable=False)
    clause_type = Column(String(100), nullable=True)
    severity = Column(String(10), nullable=True)            # INFO | LOW | MEDIUM | HIGH
    weight = Column(Integer, nullable=True)                 # weight actually applied
    reason = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    uncertain = Column(Integer, nullable=True, default=0)

    analysis = relationship("Analysis", back_populates="risk_findings")
