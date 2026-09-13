"""Contract routes: upload, list, detail, delete, text, analyze, analysis."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, Query, UploadFile

from ...core.config import Settings
from ...core.exceptions import (
    AnalysisFailure,
    ContractNotFound,
    ModelUnavailable,
    RawTextUnavailable,
)
from ...core.logging import get_logger, log_event
from ...db.repository import stats_summary
from ...schemas.analysis import (
    AnalysisResponse,
    AnalyzeAcceptedResponse,
    ClauseResultResponse,
    Entities,
    ModelInfo,
    OverallRisk,
    RiskFindingResponse,
)
from ...schemas.common import StatsResponse, RiskDistribution
from ...schemas.contract import (
    ContractListResponse,
    ContractResponse,
    DeletedResponse,
    RawTextResponse,
)
from ...services.document_parser import parse_document
from ..deps import get_service, get_settings, request_id_var
from ...services.contract_analysis import ContractAnalysisService

logger = get_logger()
router = APIRouter(prefix="/contracts", tags=["contracts"])

VALID_STATUSES = {"UPLOADED", "PARSING", "READY", "ANALYZING", "COMPLETED", "FAILED"}
VALID_SORTS = {"created_at_desc", "created_at_asc", "filename_asc", "filename_desc"}


def _file_bytes(upload: UploadFile) -> tuple[bytes, str]:
    data = upload.file.read()
    return data, upload.filename or "upload"


def _entities(clauses: list[dict]) -> Entities:
    by_label = {c.get("clause_type"): c for c in clauses}
    def text_of(label: str) -> str | None:
        c = by_label.get(label)
        return (c.get("text") or None) if (c and c.get("found")) else None
    return Entities(
        parties=text_of("parties"),
        agreement_date=text_of("agreement_date"),
        effective_date=text_of("effective_date"),
        expiration_date=text_of("expiration_date"),
        governing_law=text_of("governing_law"),
        document_name=text_of("document_name"),
    )


def _analysis_response(full: dict) -> AnalysisResponse:
    a = full.get("analysis") or {}
    return AnalysisResponse(
        analysis_id=a.get("id"),
        contract_id=full["contract"]["id"],
        status=a.get("status") or full["contract"]["status"],
        model=ModelInfo(name=a.get("model_state"), version=a.get("model_version"),
                        state=a.get("model_state")),
        overall_risk=OverallRisk(score=a.get("overall_risk_score"),
                                 level=a.get("overall_risk_level")),
        entities=_entities(full.get("clauses", [])),
        clauses=[ClauseResultResponse(**c) for c in full.get("clauses", [])],
        risk_findings=[RiskFindingResponse(**f) for f in full.get("risk_findings", [])],
        processing_ms=a.get("processing_ms"),
        disclaimer=a.get("disclaimer"),
        completed_at=a.get("completed_at"),
        error_message=a.get("error_message"),
    )


@router.post("/upload", response_model=ContractResponse, status_code=201,
             summary="Upload a contract (PDF/DOCX/TXT), validate and parse it")
def upload_contract(
    upload: UploadFile = File(...),
    service: ContractAnalysisService = Depends(get_service),
    settings: Settings = Depends(get_settings),
) -> dict:
    rid = request_id_var.get()
    data, filename = _file_bytes(upload)
    from ...utils.files import save_upload

    t0 = time.perf_counter()
    stored_path, internal_id, display_name = save_upload(data, filename, settings)
    log_event(logger, "upload", rid, filename=display_name, bytes=len(data),
              stored_as=internal_id)
    ing = service.ingest_document(stored_path, display_name)
    log_event(logger, "parsed", rid, contract_id=ing["contract_id"],
              file_type=ing["file_type"], chars=ing["character_count"],
              ms=round((time.perf_counter() - t0) * 1000, 1))
    detail = service.get_contract_detail(ing["contract_id"])
    assert detail is not None
    return detail


@router.get("", response_model=ContractListResponse, summary="List contracts with pagination/search/filters")
def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    risk_level: str | None = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    sort: str = Query("created_at_desc"),
    service: ContractAnalysisService = Depends(get_service),
) -> dict:
    if status and status not in VALID_STATUSES:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(VALID_STATUSES)}")
    if sort not in VALID_SORTS:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=f"sort must be one of {sorted(VALID_SORTS)}")
    return service.list_contracts_page(
        page=page, page_size=page_size, search=search, status=status,
        risk_level=risk_level, sort=sort,
    )


@router.get("/{contract_id}", response_model=ContractResponse,
            summary="Contract metadata + latest analysis summary (no raw text)")
def get_contract(contract_id: str, service: ContractAnalysisService = Depends(get_service)) -> dict:
    detail = service.get_contract_detail(contract_id)
    if detail is None:
        raise ContractNotFound(f"Contract '{contract_id}' was not found.")
    return detail


@router.get("/{contract_id}/text", response_model=RawTextResponse,
            summary="Raw parsed text (for evidence highlighting; requires STORE_RAW_TEXT)")
def get_contract_text(contract_id: str, service: ContractAnalysisService = Depends(get_service)):
    text, meta = service.get_raw_text(contract_id)
    if meta is None:
        raise ContractNotFound(f"Contract '{contract_id}' was not found.")
    if not text:
        raise RawTextUnavailable()
    return RawTextResponse(**meta, text=text)


@router.post("/{contract_id}/analyze", response_model=AnalyzeAcceptedResponse,
             summary="Analyze a stored contract (ML extraction + heuristic risk)")
def analyze_contract(contract_id: str, service: ContractAnalysisService = Depends(get_service)) -> dict:
    rid = request_id_var.get()
    detail = service.get_contract_detail(contract_id)
    if detail is None:
        raise ContractNotFound(f"Contract '{contract_id}' was not found.")
    log_event(logger, "analysis_started", rid, contract_id=contract_id)
    try:
        result = service.analyze_contract(contract_id)
    except ModelUnavailable:
        raise
    except AnalysisFailure as exc:
        raise
    log_event(logger, "analysis_completed", rid, contract_id=contract_id,
              analysis_id=result["analysis"]["id"],
              risk=result["analysis"]["overall_risk_level"],
              ms=result["analysis"]["processing_ms"])
    return {"analysis_id": result["analysis"]["id"], "contract_id": contract_id,
            "status": result["analysis"]["status"]}


@router.get("/{contract_id}/analysis", response_model=AnalysisResponse,
            summary="Latest analysis: overall risk, clauses, evidence, findings")
def get_analysis(contract_id: str, service: ContractAnalysisService = Depends(get_service)) -> dict:
    full = service.get_full_result(contract_id)
    if full is None:
        raise ContractNotFound(f"Contract '{contract_id}' was not found.")
    if full.get("analysis") is None:
        raise AnalysisFailure("Contract has not been analyzed yet.")
    return _analysis_response(full)


@router.delete("/{contract_id}", response_model=DeletedResponse,
               summary="Delete a contract with its analyses and stored file")
def delete_contract(contract_id: str, service: ContractAnalysisService = Depends(get_service)) -> dict:
    rid = request_id_var.get()
    deleted = service.delete_contract(contract_id)
    if not deleted:
        raise ContractNotFound(f"Contract '{contract_id}' was not found.")
    log_event(logger, "contract_deleted", rid, contract_id=contract_id)
    return {"deleted": True, "id": contract_id}


# ------------------------------------------------------------------ analyses

analyses_router = APIRouter(prefix="/analyses", tags=["analyses"])


@analyses_router.get("/{analysis_id}", response_model=AnalysisResponse,
                     summary="Fetch one analysis by id")
def get_analysis_by_id(analysis_id: int, service: ContractAnalysisService = Depends(get_service)) -> dict:
    full = service.get_analysis_result(analysis_id)
    if full is None:
        from ...core.exceptions import ContractIQError

        raise ContractNotFound(f"Analysis '{analysis_id}' was not found.")
    return _analysis_response(full)


# --------------------------------------------------------------------- stats

stats_router = APIRouter(tags=["stats"])


@stats_router.get("/stats", response_model=StatsResponse, summary="Dashboard statistics")
def get_stats(service: ContractAnalysisService = Depends(get_service)) -> dict:
    from ...db.database import session_scope

    with session_scope(service.sessions) as session:
        s = stats_summary(session)
    return StatsResponse(
        contracts_total=s["contracts"],
        completed_analyses=s["completed_analyses"],
        failed_analyses=s["failed_analyses"],
        risk_distribution=RiskDistribution(**{k: s["risk_levels"].get(k, 0)
                                              for k in ("LOW", "MEDIUM", "HIGH")}),
        avg_processing_ms=s["avg_processing_ms"],
        clauses_detected_total=s["clauses_detected_total"],
    )
