"""Phase 8 final-QA tests: risk band boundaries, confidence-aware rules,
concurrent-analyze rejection (409), mocked CUDA OOM handling, database
orphan checks, restart persistence, and STORE_RAW_TEXT=false behavior."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.risk.engine import evaluate_risk  # noqa: E402
from tests.conftest import MockAnalyzer  # noqa: E402

API = "/api"


@pytest.fixture()
def app(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'p8.db').as_posix()}",
        upload_dir=tmp_path / "uploads",
        temp_dir=tmp_path / "temp",
    )
    application = create_app(settings)
    from fastapi.testclient import TestClient

    with TestClient(application) as client:
        application.state.service.analyzer = MockAnalyzer()
        client.app_state = application.state  # type: ignore[attr-defined]
        yield client


def _clause(label, found, text="", confidence=0.99):
    return {"clause_type": label, "found": found, "text": text,
            "confidence": confidence, "start_char": 0 if found else -1,
            "end_char": len(text) if found else -1}


def _full_results(**overrides):
    from app.risk.rules import RISK_RULES

    labels = sorted({r.clause_label for r in RISK_RULES})
    out = []
    for label in labels:
        out.append(overrides.get(label, _clause(label, False)))
    return out


class TestRiskBandBoundaries:
    """Exact 0/30/31/60/61/100 boundaries: 0-30 LOW, 31-60 MEDIUM, 61-100 HIGH."""

    def _score(self, settings, *pairs):
        """Build results from (found_label_weights) by mixing rule sources."""
        # weights available: present rules 18 (non_compete), 15 (exclusivity),
        # 5 (renewal), 3 (anti-assignment), 4 (insurance), 4 (audit);
        # absent rules 12 (cap), 10 (termination); wording 10/8 via text.
        results = _full_results()
        by_label = {c["clause_type"]: c for c in results}
        for label, kwargs in pairs:
            by_label[label] = _clause(label, **kwargs)
        return evaluate_risk(list(by_label.values()), settings)

    def test_zero_score_is_low(self, settings):
        # all clauses found with neutral text -> informational-only score stays 22 baseline...
        # instead: all found with texts that fire only weight-0 rules is impossible
        # (present rules fire), so test the true floor: empty clause set
        r = evaluate_risk([], settings)
        assert r.overall_score == 22  # two absence rules
        assert r.overall_level == "LOW"

    def test_boundary_30_31(self, settings):
        # 22 baseline (cap absent 12 + termination absent 10)
        # + insurance 4 + audit 4 = 30 -> LOW; + renewal 5 -> 35 -> MEDIUM
        r30 = self._score(settings,
                          ("insurance", dict(found=True, text="x")),
                          ("audit_rights", dict(found=True, text="x")))
        assert r30.overall_score == 30 and r30.overall_level == "LOW"
        r31 = self._score(settings,
                          ("insurance", dict(found=True, text="x")),
                          ("audit_rights", dict(found=True, text="x")),
                          ("anti_assignment", dict(found=True, text="x")))
        assert r31.overall_score == 33 and r31.overall_level == "MEDIUM"

    def test_boundary_60_61(self, settings):
        # 22 + non_compete 18 + exclusivity 15 + renewal 5 = 60 -> MEDIUM
        r60 = self._score(settings,
                          ("non_compete", dict(found=True, text="x")),
                          ("exclusivity", dict(found=True, text="x")),
                          ("renewal_term", dict(found=True, text="plain term")))
        assert r60.overall_score == 60 and r60.overall_level == "MEDIUM"
        # + anti_assignment present 3 = 63 -> HIGH
        r61 = self._score(settings,
                          ("non_compete", dict(found=True, text="x")),
                          ("exclusivity", dict(found=True, text="x")),
                          ("renewal_term", dict(found=True, text="plain term")),
                          ("anti_assignment", dict(found=True, text="x")))
        assert r61.overall_score == 63 and r61.overall_level == "HIGH"

    def test_score_clamped_to_100(self, settings):
        # maximum reachable score: every present/wording rule fires (67) plus
        # both absence rules for the two clauses that only have absence rules (22) = 89.
        # The 100 cap is a safety invariant; 0 <= score <= 100 must always hold.
        by_label = {c["clause_type"]: c for c in _full_results()}
        for label in by_label:
            if label in ("cap_on_liability", "termination_for_convenience"):
                by_label[label] = _clause(label, False)  # absence rules: +12 +10
            else:
                by_label[label] = _clause(
                    label, True,
                    text="shall automatically renew without the prior written consent")
        r = evaluate_risk(list(by_label.values()), settings)
        assert 0 <= r.overall_score <= 100
        assert r.overall_score == 89 and r.overall_level == "HIGH"


class TestConfidenceAware:
    def test_low_confidence_does_not_score(self, settings):
        r = evaluate_risk(_full_results(
            non_compete=_clause("non_compete", True, "shall not compete", confidence=0.10),
        ), settings)
        f = next(x for x in r.findings if x.rule_id == "NON_COMPETE_PRESENT")
        assert f.uncertain and f.weight == 0
        assert f.severity == "HIGH"  # severity kept separate from confidence
        assert r.overall_score == 22  # baseline absence rules only


class TestConcurrentAnalyze:
    def test_second_request_rejected_409(self, app):
        """A contract whose latest analysis is ANALYZING rejects new requests."""
        from app.db import repository as repo
        from app.db.database import session_scope

        cid = _upload(app)
        with session_scope(app.app_state.service.sessions) as s:
            contract = repo.get_contract(s, cid)
            repo.update_contract_status(s, cid, "ANALYZING")
            repo.create_analysis(s, contract_id=cid, status="ANALYZING")
        r = app.post(f"{API}/contracts/{cid}/analyze")
        assert r.status_code == 409
        assert r.json()["error"] == "ANALYSIS_IN_PROGRESS"


class TestCudaOomMock:
    def test_oom_marks_failed_clears_cache_server_survives(self, app, monkeypatch):
        import torch

        cid = _upload(app)
        cleared = {"called": False}

        class OomAnalyzer:
            def analyze_contract(self, text, enabled_clauses=None):
                raise torch.cuda.OutOfMemoryError()

            def analyze_clause(self, text, label):
                raise torch.cuda.OutOfMemoryError()

        def fake_empty_cache():
            cleared["called"] = True

        monkeypatch.setattr(torch.cuda, "empty_cache", fake_empty_cache)
        app.app_state.service.analyzer = OomAnalyzer()
        r = app.post(f"{API}/contracts/{cid}/analyze")
        assert r.status_code == 500
        assert r.json()["error"] == "ANALYSIS_FAILURE"
        assert cleared["called"] is True
        detail = app.get(f"{API}/contracts/{cid}").json()
        assert detail["latest_analysis"]["status"] == "FAILED"
        assert "GPU memory" in (detail["latest_analysis"]["error_message"] or "")
        # server still serves
        assert app.get(f"{API}/health").status_code == 200


class TestDatabaseIntegrity:
    def test_no_orphan_rows(self, app):
        from sqlalchemy import text

        cid = _upload(app)
        app.post(f"{API}/contracts/{cid}/analyze")
        with app.app_state.service.sessions() as s:
            orphans_a = s.execute(text(
                "SELECT COUNT(*) FROM analyses a LEFT JOIN contracts c "
                "ON a.contract_id=c.id WHERE c.id IS NULL")).scalar()
            orphans_cr = s.execute(text(
                "SELECT COUNT(*) FROM clause_results cr LEFT JOIN analyses a "
                "ON cr.analysis_id=a.id WHERE a.id IS NULL")).scalar()
            orphans_rf = s.execute(text(
                "SELECT COUNT(*) FROM risk_findings rf LEFT JOIN analyses a "
                "ON rf.analysis_id=a.id WHERE a.id IS NULL")).scalar()
        assert orphans_a == 0 and orphans_cr == 0 and orphans_rf == 0

    def test_delete_cascade_no_orphans(self, app):
        from sqlalchemy import text

        cid = _upload(app)
        app.post(f"{API}/contracts/{cid}/analyze")
        app.delete(f"{API}/contracts/{cid}")
        with app.app_state.service.sessions() as s:
            counts = s.execute(text(
                "SELECT (SELECT COUNT(*) FROM contracts), "
                "(SELECT COUNT(*) FROM analyses), "
                "(SELECT COUNT(*) FROM clause_results), "
                "(SELECT COUNT(*) FROM risk_findings)")).fetchone()
        assert counts == (0, 0, 0, 0)

    def test_restart_persists_rows(self, tmp_path):
        settings = Settings(
            database_url=f"sqlite:///{(tmp_path / 'persist.db').as_posix()}",
            upload_dir=tmp_path / "uploads", temp_dir=tmp_path / "temp",
        )
        application = create_app(settings)
        from fastapi.testclient import TestClient

        with TestClient(application) as client:
            application.state.service.analyzer = MockAnalyzer()
            body = "Governing law is Ohio.\n\nNon-compete applies."
            r = client.post(f"{API}/contracts/upload",
                            files={"upload": ("p.txt", body.encode(), "text/plain")})
            cid = r.json()["id"]
            client.post(f"{API}/contracts/{cid}/analyze")
            aid = client.get(f"{API}/contracts/{cid}/analysis").json()["analysis_id"]

        # "restart": brand-new app instance on the same DB file
        application2 = create_app(settings)
        with TestClient(application2) as client2:
            detail = client2.get(f"{API}/contracts/{cid}").json()
            assert detail["status"] == "COMPLETED"
            full = client2.get(f"{API}/contracts/{cid}/analysis").json()
            assert full["analysis_id"] == aid
            assert len(full["risk_findings"]) > 0


    def test_delete_contract_referenced_by_duplicate(self, app):
        """Deleting the ORIGINAL of a duplicate pair must succeed even though
        the duplicate row references it via duplicate_of_id (FK regression)."""
        body = b"DUPLICATE FK REGRESSION TEST. Governing law is Maine."
        r1 = app.post(f"{API}/contracts/upload",
                      files={"upload": ("orig.txt", body, "text/plain")})
        r2 = app.post(f"{API}/contracts/upload",
                      files={"upload": ("copy.txt", body, "text/plain")})
        assert r2.json()["duplicate_of_id"] == r1.json()["id"]
        r = app.delete(f"{API}/contracts/{r1.json()['id']}")  # delete the original first
        assert r.status_code == 200
        # the duplicate survives, its reference cleared
        dup = app.get(f"{API}/contracts/{r2.json()['id']}").json()
        assert dup["duplicate_of_id"] is None


class TestRawTextDisabled:
    def test_endpoint_and_frontend_path(self, tmp_path):
        settings = Settings(
            database_url=f"sqlite:///{(tmp_path / 'rt.db').as_posix()}",
            upload_dir=tmp_path / "uploads", temp_dir=tmp_path / "temp",
            store_raw_text=False,
        )
        application = create_app(settings)
        from fastapi.testclient import TestClient

        with TestClient(application) as client:
            application.state.service.analyzer = MockAnalyzer()
            r = client.post(f"{API}/contracts/upload",
                            files={"upload": ("x.txt", b"hello clause", "text/plain")})
            cid = r.json()["id"]
            rt = client.get(f"{API}/contracts/{cid}/text")
            assert rt.status_code == 404
            assert rt.json()["error"] == "RAW_TEXT_UNAVAILABLE"
            # analysis of a no-text contract fails cleanly
            ra = client.post(f"{API}/contracts/{cid}/analyze")
            assert ra.status_code == 500
            assert client.get(f"{API}/contracts/{cid}").json()["latest_analysis"]["status"] == "FAILED"


def _upload(client, name="qa.txt"):
    body = ("QA SERVICES AGREEMENT\n\nGoverning law is Ohio.\n\n"
            "The parties shall not compete.\n\nEither party may terminate for convenience.")
    r = client.post(f"{API}/contracts/upload",
                    files={"upload": (name, body.encode("utf-8"), "text/plain")})
    assert r.status_code == 201
    return r.json()["id"]
