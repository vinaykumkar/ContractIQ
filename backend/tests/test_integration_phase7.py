"""Phase 7 integration tests (API level, mocked analyzer — fast).

Covers the hardening behaviors: full flow, exact evidence-offset consistency,
idempotent re-analysis, failure/model-unavailable recovery, delete cascade,
history/stats consistency, CORS preflight, evidence edge cases (beginning /
end / multiline / unicode / repeated sentences), and stale-ANALYZING recovery.
"""
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
from tests.conftest import MockAnalyzer  # noqa: E402

API = "/api"


@pytest.fixture()
def app(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'p7.db').as_posix()}",
        upload_dir=tmp_path / "uploads",
        temp_dir=tmp_path / "temp",
    )
    application = create_app(settings)
    from fastapi.testclient import TestClient

    with TestClient(application) as client:
        # default to the mock analyzer for speed; individual tests may replace it
        application.state.service.analyzer = MockAnalyzer()
        client.app_state = application.state  # type: ignore[attr-defined]
        yield client


def _upload(client, name="integration.txt", text: str | None = None):
    body = text or """MASTER SERVICES AGREEMENT

This agreement is made by and between Acme Corp and Beta LLC on 1 May 2025.

1. NON-COMPETE. Supplier shall not compete with the Company for two years.
2. GOVERNING LAW. This agreement is governed by the laws of the State of Ohio.
"""
    r = client.post(f"{API}/contracts/upload",
                    files={"upload": (name, body.encode("utf-8"), "text/plain")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestFullFlow:
    def test_upload_analyze_retrieve(self, app):
        cid = _upload(app)
        ra = app.post(f"{API}/contracts/{cid}/analyze")
        assert ra.status_code == 200
        aid = ra.json()["analysis_id"]
        full = app.get(f"{API}/contracts/{cid}/analysis").json()
        assert full["analysis_id"] == aid
        assert full["status"] == "COMPLETED"
        assert full["overall_risk"]["level"] == "HIGH"
        assert full["model"]["state"] == "fine_tuned"
        assert len(full["clauses"]) == 7  # MockAnalyzer covers 7 clause labels

    def test_contract_metadata_without_raw_text(self, app):
        cid = _upload(app)
        body = app.get(f"{API}/contracts/{cid}").json()
        assert "text" not in body
        assert body["status"] == "READY"


class TestEvidenceOffsets:
    def test_offsets_match_stored_text_exactly(self, app):
        """Critical invariant: clause offsets index the exact /text payload."""
        text = ("INLINE HEADER CLAUSE. Supplier shall not compete with the Company. "
                "Middle filler text. The agreement is governed by the laws of the State of Ohio. "
                "TAIL CLAUSE STATEMENT for the end of the document.")
        cid = _upload(app, text=text)
        app.app_state.service.analyzer = MockAnalyzer(findings={
            "non_compete": {"found": True, "text": "Supplier shall not compete with the Company",
                            "confidence": 0.9,
                            "start_char": text.index("Supplier shall not compete"),
                            "end_char": text.index("Supplier shall not compete") + len("Supplier shall not compete with the Company")},
            "governing_law": {"found": True, "text": "governed by the laws of the State of Ohio",
                              "confidence": 0.9,
                              "start_char": text.index("governed by the laws"),
                              "end_char": text.index("governed by the laws") + len("governed by the laws of the State of Ohio")},
        })
        app.post(f"{API}/contracts/{cid}/analyze")
        stored = app.get(f"{API}/contracts/{cid}/text").json()["text"]
        full = app.get(f"{API}/contracts/{cid}/analysis").json()
        for c in full["clauses"]:
            if c["found"]:
                assert stored[c["start_char"]:c["end_char"]] == c["text"], c["clause_type"]

    @pytest.mark.parametrize("placement", ["beginning", "end", "multiline", "unicode", "repeated"])
    def test_evidence_edge_cases(self, app, placement):
        base = "X" * 50
        if placement == "beginning":
            text = "NON-COMPETE CLAUSE at the very start. " + base
            needle = "NON-COMPETE CLAUSE at the very start."
        elif placement == "end":
            text = base + " ending with the non-compete sentence here."
            needle = "ending with the non-compete sentence here."
        elif placement == "multiline":
            text = base + "\n\nMulti\nline\nnon compete clause spanning lines."
            needle = "Multi\nline\nnon compete clause spanning lines."
        elif placement == "unicode":
            text = base + " Café naïve — “quoted” non-compete §5 clause ✓."
            needle = "Café naïve — “quoted” non-compete §5 clause ✓."
        else:  # repeated sentence
            sentence = "The parties shall not compete in any market."
            text = f"{sentence} Filler. {sentence} More filler. {sentence}"
            needle = sentence
        cid = _upload(app, text=text)
        app.app_state.service.analyzer = MockAnalyzer(findings={
            "non_compete": {"found": True, "text": needle, "confidence": 0.9,
                            "start_char": text.index(needle),
                            "end_char": text.index(needle) + len(needle)},
        })
        app.post(f"{API}/contracts/{cid}/analyze")
        stored = app.get(f"{API}/contracts/{cid}/text").json()["text"]
        full = app.get(f"{API}/contracts/{cid}/analysis").json()
        c = next(x for x in full["clauses"] if x["clause_type"] == "non_compete")
        assert stored[c["start_char"]:c["end_char"]] == needle


class TestAnalyzeIdempotencyAndRecovery:
    def test_second_analyze_returns_same_analysis(self, app):
        """Re-analysis policy (Option A): COMPLETED contract returns the
        existing analysis - no duplicate versions."""
        cid = _upload(app)
        a1 = app.post(f"{API}/contracts/{cid}/analyze").json()["analysis_id"]
        a2 = app.post(f"{API}/contracts/{cid}/analyze").json()["analysis_id"]
        assert a1 == a2
        analyses = app.get(f"{API}/contracts/{cid}/analysis").json()
        assert analyses["analysis_id"] == a1

    def test_failed_analysis_can_be_retried(self, app):
        cid = _upload(app)
        app.app_state.service.analyzer = MockAnalyzer(fail=True)
        assert app.post(f"{API}/contracts/{cid}/analyze").status_code == 500
        detail = app.get(f"{API}/contracts/{cid}").json()
        assert detail["status"] == "FAILED"
        # explicit retry with a working analyzer succeeds
        app.app_state.service.analyzer = MockAnalyzer()
        ra = app.post(f"{API}/contracts/{cid}/analyze")
        assert ra.status_code == 200
        assert app.get(f"{API}/contracts/{cid}/analysis").json()["status"] == "COMPLETED"

    def test_stale_analyzing_recovered_at_startup(self, tmp_path):
        """An ANALYZING row left by a crashed process must be FAILED at next
        startup and the contract must be retryable."""
        from app.db.database import get_engine, init_db, make_session_factory, session_scope
        from app.db import repository as repo

        settings = Settings(
            database_url=f"sqlite:///{(tmp_path / 'stale.db').as_posix()}",
            upload_dir=tmp_path / "uploads", temp_dir=tmp_path / "temp",
        )
        # simulate a crashed run: insert a contract + ANALYZING analysis directly
        engine = get_engine(settings.database_url)
        init_db(engine)
        factory = make_session_factory(engine)
        with session_scope(factory) as s:
            repo.create_contract(s, contract_id="STALE1", filename="x.txt",
                                 original_filename="x.txt", file_type="txt",
                                 status="ANALYZING", raw_text="Governing law is Ohio.")
            repo.create_analysis(s, contract_id="STALE1", status="ANALYZING")
        engine.dispose()

        # new app instance on the same DB: startup recovery must fix it
        application = create_app(settings)
        from fastapi.testclient import TestClient

        with TestClient(application) as client:
            detail = client.get(f"{API}/contracts/STALE1").json()
            assert detail["status"] == "FAILED"
            assert detail["latest_analysis"]["status"] == "FAILED"
            assert "restart" in (detail["latest_analysis"]["error_message"] or "")
            # and analysis is retryable
            application.state.service.analyzer = MockAnalyzer()
            assert client.post(f"{API}/contracts/STALE1/analyze").status_code == 200


class TestModelUnavailable:
    def test_503_envelope_and_failed_state(self, app):
        from app.core.exceptions import ModelUnavailable

        class Broken:
            def analyze_contract(self, text, enabled_clauses=None):
                raise ModelUnavailable("missing model")

            def analyze_clause(self, text, label):
                raise ModelUnavailable("missing model")

        cid = _upload(app)
        app.app_state.service.analyzer = Broken()
        r = app.post(f"{API}/contracts/{cid}/analyze")
        assert r.status_code == 503
        body = r.json()
        assert body["error"] == "MODEL_UNAVAILABLE"
        assert body["request_id"]
        assert app.get(f"{API}/contracts/{cid}").json()["latest_analysis"]["status"] == "FAILED"


class TestHistoryStatsDelete:
    def test_history_and_stats_consistency(self, app):
        r0 = app.get(f"{API}/stats").json()
        assert r0["contracts_total"] == 0
        cid = _upload(app)
        # after upload (before analysis): READY, no risk
        listing = app.get(f"{API}/contracts", params={"status": "READY"}).json()
        assert listing["total"] == 1
        assert app.get(f"{API}/stats").json()["completed_analyses"] == 0
        # after analysis: COMPLETED with risk level
        app.post(f"{API}/contracts/{cid}/analyze")
        assert app.get(f"{API}/contracts", params={"risk_level": "HIGH"}).json()["total"] == 1
        s = app.get(f"{API}/stats").json()
        assert s["completed_analyses"] == 1 and s["risk_distribution"]["HIGH"] == 1
        assert s["clauses_detected_total"] > r0["clauses_detected_total"]
        assert s["avg_processing_ms"] is not None

    def test_delete_cascades_and_cleans_file(self, app):
        cid = _upload(app)
        app.post(f"{API}/contracts/{cid}/analyze")
        r = app.delete(f"{API}/contracts/{cid}")
        assert r.status_code == 200
        assert app.get(f"{API}/contracts/{cid}").status_code == 404
        assert app.get(f"{API}/contracts/{cid}/analysis").status_code == 404
        assert app.get(f"{API}/contracts/{cid}/text").status_code == 404
        assert app.get(f"{API}/stats").json()["contracts_total"] == 0

    def test_duplicate_upload_is_flagged_not_hidden(self, app):
        first = _upload(app, name="doc.txt")
        second = _upload(app, name="copy.txt")
        assert second != first
        detail = app.get(f"{API}/contracts/{second}").json()
        assert detail["duplicate_of_id"] == first


class TestCorsAndErrors:
    def test_cors_preflight_and_headers(self, app):
        r = app.options(f"{API}/contracts", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        })
        assert r.status_code in (200, 400)
        assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_error_envelope_shape_on_all_errors(self, app):
        for path, method in [
            (f"{API}/contracts/none", "get"),
            (f"{API}/contracts/none/analysis", "get"),
            (f"{API}/contracts/none/text", "get"),
            (f"{API}/analyses/424242", "get"),
        ]:
            r = getattr(app, method)(path)
            assert r.status_code in (404, 500)
            body = r.json()
            assert set(body) >= {"error", "message", "request_id"}

    def test_health_reports_model_state(self, app):
        body = app.get(f"{API}/health").json()
        assert body["model"]["available"] in (True, False)
        assert body["model"]["device"] in ("cpu", "cuda")
