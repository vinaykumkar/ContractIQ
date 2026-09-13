"""Repository layer: the ONLY place that touches SQLAlchemy queries.

Services call these functions with an explicit Session; transactions are
managed by db.database.session_scope (commit on success, rollback on error).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import models

# contract statuses: UPLOADED, PARSING, ANALYZING, COMPLETED, FAILED
# analysis statuses: ANALYZING, COMPLETED, FAILED


def create_contract(
    session: Session,
    *,
    contract_id: str,
    filename: str,
    original_filename: str,
    file_type: str,
    character_count: int | None = None,
    page_count: int | None = None,
    text_hash: str | None = None,
    parser_warnings: list[str] | None = None,
    stored_path: str | None = None,
    raw_text: str | None = None,
    duplicate_of_id: str | None = None,
    status: str = "UPLOADED",
) -> models.Contract:
    contract = models.Contract(
        id=contract_id,
        filename=filename,
        original_filename=original_filename,
        file_type=file_type,
        character_count=character_count,
        page_count=page_count,
        text_hash=text_hash,
        parser_warnings=json.dumps(parser_warnings or [], ensure_ascii=False),
        stored_path=stored_path,
        raw_text=raw_text,
        duplicate_of_id=duplicate_of_id,
        status=status,
    )
    session.add(contract)
    session.flush()
    return contract


def get_contract(session: Session, contract_id: str) -> models.Contract | None:
    return session.get(models.Contract, contract_id)


def find_contract_by_hash(session: Session, text_hash: str) -> models.Contract | None:
    if not text_hash:
        return None
    stmt = select(models.Contract).where(models.Contract.text_hash == text_hash).limit(1)
    return session.execute(stmt).scalar_one_or_none()


def list_contracts(
    session: Session,
    *,
    search: str | None = None,
    risk_level: str | None = None,
    status: str | None = None,
    sort: str = "created_at_desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[models.Contract], int]:
    """Contracts page + total count for pagination."""
    stmt = select(models.Contract)
    if search:
        stmt = stmt.where(models.Contract.filename.like(f"%{search}%"))
    if status:
        stmt = stmt.where(models.Contract.status == status)
    if risk_level:
        # contracts whose LATEST completed analysis has this overall level
        latest_ids = (
            select(func.max(models.Analysis.id))
            .where(models.Analysis.status == "COMPLETED")
            .group_by(models.Analysis.contract_id)
        )
        matching = (
            select(models.Analysis.contract_id)
            .where(models.Analysis.id.in_(latest_ids))
            .where(models.Analysis.overall_risk_level == risk_level)
        )
        stmt = stmt.where(models.Contract.id.in_(matching))
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    order = (
        models.Contract.created_at.asc() if sort == "created_at_asc"
        else models.Contract.filename.asc() if sort == "filename_asc"
        else models.Contract.filename.desc() if sort == "filename_desc"
        else models.Contract.created_at.desc()
    )
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    items = list(session.execute(stmt).scalars().all())
    return items, int(total)


def update_contract_status(session: Session, contract_id: str, status: str) -> models.Contract | None:
    contract = session.get(models.Contract, contract_id)
    if contract:
        contract.status = status
        session.flush()
    return contract


def delete_contract(session: Session, contract_id: str) -> bool:
    contract = session.get(models.Contract, contract_id)
    if not contract:
        return False
    # clear duplicate references first: contracts.duplicate_of_id is a self-FK
    # with no cascade, so deleting a referenced original would otherwise fail
    session.query(models.Contract).filter(
        models.Contract.duplicate_of_id == contract_id
    ).update({"duplicate_of_id": None})
    session.delete(contract)  # cascades to analyses/clauses/findings
    session.flush()
    return True


# ------------------------------------------------------------------ analyses

def create_analysis(
    session: Session,
    *,
    contract_id: str,
    model_name: str | None = None,
    model_version: str | None = None,
    model_state: str | None = None,
    status: str = "ANALYZING",
) -> models.Analysis:
    analysis = models.Analysis(
        contract_id=contract_id,
        model_name=model_name,
        model_version=model_version,
        model_state=model_state,
        started_at=datetime.now(timezone.utc),
        status=status,
    )
    session.add(analysis)
    session.flush()
    return analysis


def complete_analysis(
    session: Session,
    analysis: models.Analysis,
    *,
    processing_ms: float | None = None,
    overall_risk_score: int | None = None,
    overall_risk_level: str | None = None,
    disclaimer: str | None = None,
) -> models.Analysis:
    analysis.completed_at = datetime.now(timezone.utc)
    analysis.processing_ms = processing_ms
    analysis.overall_risk_score = overall_risk_score
    analysis.overall_risk_level = overall_risk_level
    analysis.status = "COMPLETED"
    analysis.disclaimer = disclaimer
    session.flush()
    return analysis


def fail_analysis(session: Session, analysis: models.Analysis, error_message: str) -> models.Analysis:
    analysis.completed_at = datetime.now(timezone.utc)
    analysis.status = "FAILED"
    analysis.error_message = error_message
    session.flush()
    return analysis


def save_clause_results(session: Session, analysis_id: int, results: list[dict]) -> list[models.ClauseResult]:
    rows = [
        models.ClauseResult(
            analysis_id=analysis_id,
            clause_type=r["clause_type"],
            found=1 if r.get("found") else 0,
            extracted_text=r.get("text") or "",
            confidence=r.get("confidence"),
            start_char=r.get("start_char"),
            end_char=r.get("end_char"),
            risk_level=r.get("risk_level"),
            risk_reason=r.get("risk_reason"),
            uncertain=1 if r.get("uncertain") else 0,
        )
        for r in results
    ]
    session.add_all(rows)
    session.flush()
    return rows


def save_risk_findings(session: Session, analysis_id: int, findings: list[dict]) -> list[models.RiskFinding]:
    rows = [
        models.RiskFinding(
            analysis_id=analysis_id,
            rule_id=f["rule_id"],
            clause_type=f.get("clause_type"),
            severity=f.get("severity"),
            weight=f.get("weight"),
            reason=f.get("reason"),
            evidence=f.get("evidence"),
            confidence=f.get("confidence"),
            uncertain=1 if f.get("uncertain") else 0,
        )
        for f in findings
    ]
    session.add_all(rows)
    session.flush()
    return rows


def get_analysis(session: Session, analysis_id: int) -> models.Analysis | None:
    return session.get(models.Analysis, analysis_id)


def latest_analysis(session: Session, contract_id: str) -> models.Analysis | None:
    stmt = (
        select(models.Analysis)
        .where(models.Analysis.contract_id == contract_id)
        .order_by(models.Analysis.id.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def analyses_for_contract(session: Session, contract_id: str) -> list[models.Analysis]:
    stmt = (
        select(models.Analysis)
        .where(models.Analysis.contract_id == contract_id)
        .order_by(models.Analysis.id.desc())
    )
    return list(session.execute(stmt).scalars().all())


def stats_summary(session: Session) -> dict:
    n_contracts = session.execute(select(func.count(models.Contract.id))).scalar() or 0
    n_completed = session.execute(
        select(func.count(models.Analysis.id)).where(models.Analysis.status == "COMPLETED")
    ).scalar() or 0
    n_failed = session.execute(
        select(func.count(models.Analysis.id)).where(models.Analysis.status == "FAILED")
    ).scalar() or 0
    avg_ms = session.execute(
        select(func.avg(models.Analysis.processing_ms)).where(models.Analysis.status == "COMPLETED")
    ).scalar()
    by_level = dict(session.execute(
        select(models.Analysis.overall_risk_level, func.count(models.Analysis.id))
        .where(models.Analysis.status == "COMPLETED")
        .group_by(models.Analysis.overall_risk_level)
    ).all())
    clauses_total = session.execute(
        select(func.count(models.ClauseResult.id)).where(models.ClauseResult.found == 1)
    ).scalar() or 0
    return {
        "contracts": n_contracts,
        "completed_analyses": n_completed,
        "failed_analyses": n_failed,
        "avg_processing_ms": round(float(avg_ms), 1) if avg_ms is not None else None,
        "risk_levels": {k: v for k, v in by_level.items() if k},
        "clauses_detected_total": int(clauses_total),
    }
