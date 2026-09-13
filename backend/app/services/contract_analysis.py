"""Contract analysis coordination service.

Pipeline (one place, no ML/backend coupling):

    stored file -> parser -> ParsedDocument -> (hash, duplicate check)
    -> Contract row (UPLOADED -> PARSING -> ANALYZING)
    -> ML adapter (Phase 3 inference API) -> clause findings
    -> heuristic risk engine -> per-clause risk levels
    -> single-transaction persistence (Analysis + ClauseResults + RiskFindings)
    -> COMPLETED (or FAILED with a clean error message)

The analyzer is injected (MLAnalyzerAdapter in production, a stub in tests) so
tests never run the transformer.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

from ..core.config import Settings, load_settings
from ..core.exceptions import AnalysisFailure, AnalysisInProgress, ContractIQError, ParseError
from ..db import repository as repo
from ..db.database import init_db, make_session_factory, session_scope
from ..risk.engine import evaluate_risk
from .document_parser import ParsedDocument, parse_document
from .ml_adapter import MLAnalyzerAdapter

DISCLAIMER = "AI-assisted analysis. Results should be reviewed by a qualified professional."


def _cuda_oom_type():
    """torch.cuda.OutOfMemoryError when torch is loaded; ()-type (never matches) otherwise."""
    try:
        from torch.cuda import OutOfMemoryError

        return OutOfMemoryError
    except Exception:
        return ()


def normalize_text_for_hash(text: str) -> str:
    """Whitespace-collapsed text so trivial formatting changes don't dodge dedup."""
    return " ".join(text.split())


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text_for_hash(text).encode("utf-8")).hexdigest()


class ContractAnalysisService:
    def __init__(self, *, analyzer=None, settings: Settings | None = None, engine=None):
        self.settings = settings or load_settings()
        self.settings.ensure_storage_dirs()
        self.analyzer = analyzer or MLAnalyzerAdapter(self.settings.ml_model_config)
        self._engine = engine

    # ------------------------------------------------------------- plumbing

    @property
    def engine(self):
        if self._engine is None:
            from ..db.database import get_engine

            self._engine = get_engine(self.settings.database_url)
            init_db(self._engine)
        return self._engine

    def close(self) -> None:
        """Dispose the lazily-created engine (app shutdown / tests)."""
        if self._engine is not None:
            try:
                self._engine.dispose()
            finally:
                self._engine = None

    @property
    def sessions(self):
        if not hasattr(self, "_sessions"):
            self._sessions = make_session_factory(self.engine)
        return self._sessions

    # ------------------------------------------------------------ ingestion

    def ingest_document(self, path: Path, original_filename: str | None = None) -> dict:
        """Parse a stored upload and persist the Contract row.

        Returns a dict with contract_id, parse metadata and duplicate info.
        Raises ParseError subclasses on unreadable documents.
        """
        parsed = parse_document(path, original_filename or path.name)
        # display name: the sanitized original as provided by the caller
        display_name = original_filename or parsed.original_filename or parsed.filename

        with session_scope(self.sessions) as session:
            duplicate = repo.find_contract_by_hash(session, text_hash(parsed.text))
            contract = repo.create_contract(
                session,
                contract_id=uuid.uuid4().hex,
                filename=display_name,
                original_filename=parsed.original_filename,
                file_type=parsed.file_type,
                character_count=parsed.character_count,
                page_count=parsed.page_count,
                text_hash=text_hash(parsed.text),
                parser_warnings=parsed.warnings,
                stored_path=str(path),
                raw_text=parsed.text if self.settings.store_raw_text else None,
                duplicate_of_id=duplicate.id if duplicate else None,
                status="UPLOADED",
            )
            # parse completed within this request: ready to be analyzed
            repo.update_contract_status(session, contract.id, "READY")
        return {
            "contract_id": contract.id,
            "filename": contract.filename,
            "file_type": contract.file_type,
            "character_count": parsed.character_count,
            "page_count": parsed.page_count,
            "warnings": parsed.warnings,
            "duplicate_of": duplicate.id if duplicate else None,
        }

    # ------------------------------------------------------------- analysis

    def recover_stale_analyses(self) -> int:
        """Mark analyses stuck in ANALYZING (e.g. after a process crash) as FAILED.

        Called once at app startup: a synchronous analysis can only be running
        inside this process, so any ANALYZING row at startup is stale and safe
        to fail. Returns the number of recovered rows.
        """
        from ..db import models

        recovered = 0
        with session_scope(self.sessions) as session:
            stuck = session.query(models.Analysis).filter(models.Analysis.status == "ANALYZING").all()
            for a in stuck:
                repo.fail_analysis(session, a, "Analysis interrupted by application restart; safe to retry.")
                repo.update_contract_status(session, a.contract_id, "FAILED")
                recovered += 1
        if recovered:
            from ..core.logging import get_logger, log_event

            log_event(get_logger(), "stale_analyses_recovered", count=recovered)
        return recovered

    def analyze_contract(self, contract_id: str) -> dict:
        """Run the full analysis for a stored contract and persist everything.

        Policy (documented): analyzing an already-COMPLETED contract returns
        the existing latest analysis (idempotent - no duplicate versions);
        while an analysis is running a second request raises AnalysisInProgress.
        """
        failure_message: str | None = None
        with session_scope(self.sessions) as session:
            contract = repo.get_contract(session, contract_id)
            if contract is None:
                raise AnalysisFailure(f"Contract '{contract_id}' not found.")
            latest = repo.latest_analysis(session, contract_id)
            if latest is not None:
                if latest.status == "COMPLETED":
                    return self._build_result(session, contract_id, latest)
                if latest.status == "ANALYZING":
                    raise AnalysisInProgress()
            if not contract.raw_text:
                # persist the failure FIRST (commit), then raise - otherwise
                # session_scope would roll the FAILED status back
                failure_message = (
                    "Raw text not available (STORE_RAW_TEXT disabled or text lost); "
                    "cannot analyze."
                )
                repo.update_contract_status(session, contract_id, "FAILED")
                analysis = repo.create_analysis(session, contract_id=contract_id, status="FAILED")
                repo.fail_analysis(session, analysis, failure_message)
            else:
                repo.update_contract_status(session, contract_id, "ANALYZING")
                analysis = repo.create_analysis(session, contract_id=contract_id)
        if failure_message is not None:
            raise AnalysisFailure(failure_message)

        # model runs OUTSIDE the DB transaction (long); failures are persisted after
        t0 = time.perf_counter()
        try:
            ml_result = self.analyzer.analyze_contract(contract.raw_text)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            if isinstance(exc, _cuda_oom_type()):
                # CUDA OOM: free the cache so the server keeps serving requests
                try:
                    import torch

                    torch.cuda.empty_cache()
                except Exception:
                    pass
                message = "GPU memory exhausted while analyzing this document. Try a shorter document."
            with session_scope(self.sessions) as session:
                a = repo.get_analysis(session, analysis.id)
                repo.fail_analysis(session, a, message)
                repo.update_contract_status(session, contract_id, "FAILED")
            if isinstance(exc, ContractIQError):
                # domain errors (e.g. ModelUnavailable) keep their API mapping
                raise
            raise AnalysisFailure(message) from exc

        elapsed_ms = (time.perf_counter() - t0) * 1000
        clause_results = ml_result.get("clauses", [])

        # heuristic risk on the ML findings
        risk = evaluate_risk(clause_results, self.settings)

        # per-clause risk level/reason for the UI (separate from ML confidence)
        findings_by_clause: dict[str, list] = {}
        for f in risk.findings:
            findings_by_clause.setdefault(f.clause_type, []).append(f)
        for cr in clause_results:
            fs = findings_by_clause.get(cr.get("clause_type"), [])
            certain = [f for f in fs if not f.uncertain]
            cr["risk_level"] = max(
                (f.severity for f in certain),
                key=lambda s: {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(s, 0),
                default=None,
            )
            cr["risk_reason"] = "; ".join(f.reason for f in fs) or None
            cr["uncertain"] = any(f.uncertain for f in fs)

        # persist results atomically: analysis + clauses + findings together
        with session_scope(self.sessions) as session:
            a = repo.get_analysis(session, analysis.id)
            a.model_name = ml_result.get("model_state")
            a.model_version = ml_result.get("model_version")
            a.model_state = ml_result.get("model_state")
            repo.save_clause_results(session, a.id, clause_results)
            repo.save_risk_findings(session, a.id, [f.to_dict() for f in risk.findings])
            repo.complete_analysis(
                session, a,
                processing_ms=round(elapsed_ms, 1),
                overall_risk_score=risk.overall_score,
                overall_risk_level=risk.overall_level,
                disclaimer=DISCLAIMER,
            )
            repo.update_contract_status(session, contract_id, "COMPLETED")
            result = self._build_result(session, contract_id, a)

        return result

    # -------------------------------------------------------------- reading

    def get_full_result(self, contract_id: str) -> dict | None:
        with session_scope(self.sessions) as session:
            contract = repo.get_contract(session, contract_id)
            if contract is None:
                return None
            analysis = repo.latest_analysis(session, contract_id)
            if analysis is None:
                # ingested but not yet analyzed
                return {
                    "contract": {
                        "id": contract.id,
                        "filename": contract.filename,
                        "file_type": contract.file_type,
                        "created_at": contract.created_at.isoformat() if contract.created_at else None,
                        "character_count": contract.character_count,
                        "page_count": contract.page_count,
                        "status": contract.status,
                        "text": contract.raw_text or "",
                    },
                    "analysis": None,
                    "clauses": [],
                    "risk_findings": [],
                }
            return self._build_result(session, contract_id, analysis)

    def get_analysis_result(self, analysis_id: int) -> dict | None:
        with session_scope(self.sessions) as session:
            analysis = repo.get_analysis(session, analysis_id)
            if analysis is None:
                return None
            return self._build_result(session, analysis.contract_id, analysis)

    def list_contracts_page(
        self, *, page: int = 1, page_size: int = 20, search: str | None = None,
        status: str | None = None, risk_level: str | None = None, sort: str = "created_at_desc",
    ) -> dict:
        with session_scope(self.sessions) as session:
            items, total = repo.list_contracts(
                session, search=search, risk_level=risk_level, status=status,
                sort=sort, limit=page_size, offset=(page - 1) * page_size,
            )
            rows = []
            for c in items:
                latest = repo.latest_analysis(session, c.id)
                rows.append({
                    "id": c.id,
                    "filename": c.filename,
                    "file_type": c.file_type,
                    "status": c.status,
                    "character_count": c.character_count,
                    "page_count": c.page_count,
                    "parser_warnings": json.loads(c.parser_warnings or "[]"),
                    "duplicate_of_id": c.duplicate_of_id,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "latest_analysis": self._analysis_summary(latest),
                })
            return {"total": total, "page": page, "page_size": page_size, "items": rows}

    def get_contract_detail(self, contract_id: str) -> dict | None:
        """Contract metadata + latest analysis summary; NO raw text."""
        with session_scope(self.sessions) as session:
            c = repo.get_contract(session, contract_id)
            if c is None:
                return None
            latest = repo.latest_analysis(session, c.id)
            return {
                "id": c.id,
                "filename": c.filename,
                "file_type": c.file_type,
                "status": c.status,
                "character_count": c.character_count,
                "page_count": c.page_count,
                "parser_warnings": json.loads(c.parser_warnings or "[]"),
                "duplicate_of_id": c.duplicate_of_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "latest_analysis": self._analysis_summary(latest),
            }

    def get_raw_text(self, contract_id: str) -> tuple[str | None, dict | None]:
        """Raw text for highlighting; (None, meta) when retention is disabled."""
        with session_scope(self.sessions) as session:
            c = repo.get_contract(session, contract_id)
            if c is None:
                return None, None
            meta = {"id": c.id, "filename": c.filename,
                    "character_count": c.character_count or 0}
            return (c.raw_text or ""), meta

    def delete_contract(self, contract_id: str) -> bool:
        """Delete contract + cascades + stored upload file (path contained)."""
        with session_scope(self.sessions) as session:
            c = repo.get_contract(session, contract_id)
            if c is None:
                return False
            stored = c.stored_path
            deleted = repo.delete_contract(session, contract_id)
        if deleted and stored:
            from ..utils.files import delete_stored_file

            p = Path(stored)
            # containment guard: only delete files inside the configured upload dir
            try:
                if p.resolve().is_relative_to(self.settings.upload_dir.resolve()):
                    delete_stored_file(p)
            except (OSError, ValueError):
                pass
        return deleted

    @staticmethod
    def _analysis_summary(a) -> dict | None:
        if a is None:
            return None
        return {
            "id": a.id,
            "status": a.status,
            "overall_risk_score": a.overall_risk_score,
            "overall_risk_level": a.overall_risk_level,
            "model_state": a.model_state,
            "model_version": a.model_version,
            "processing_ms": a.processing_ms,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "error_message": a.error_message,
        }

    def _build_result(self, session, contract_id: str, analysis) -> dict:
        contract = repo.get_contract(session, contract_id)
        clauses = [
            {
                "clause_type": c.clause_type,
                "found": bool(c.found),
                "text": c.extracted_text or "",
                "confidence": c.confidence,
                "start_char": c.start_char,
                "end_char": c.end_char,
                "risk_level": c.risk_level,
                "risk_reason": c.risk_reason,
                "uncertain": bool(c.uncertain),
            }
            for c in analysis.clause_results
        ]
        findings = [
            {
                "rule_id": f.rule_id,
                "clause_type": f.clause_type,
                "severity": f.severity,
                "weight": f.weight,
                "reason": f.reason,
                "evidence": f.evidence,
                "confidence": f.confidence,
                "uncertain": bool(f.uncertain),
            }
            for f in analysis.risk_findings
        ]
        return {
            "contract": {
                "id": contract.id,
                "filename": contract.filename,
                "file_type": contract.file_type,
                "created_at": contract.created_at.isoformat() if contract.created_at else None,
                "character_count": contract.character_count,
                "page_count": contract.page_count,
                "status": contract.status,
                "text": contract.raw_text or "",
            },
            "analysis": {
                "id": analysis.id,
                "status": analysis.status,
                "model_state": analysis.model_state,
                "model_version": analysis.model_version,
                "processing_ms": analysis.processing_ms,
                "overall_risk_score": analysis.overall_risk_score,
                "overall_risk_level": analysis.overall_risk_level,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                "error_message": analysis.error_message,
                "disclaimer": analysis.disclaimer or DISCLAIMER,
            },
            "clauses": clauses,
            "risk_findings": findings,
        }
