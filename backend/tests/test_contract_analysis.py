"""Contract analysis service tests: full pipeline with a mocked analyzer,
model-unavailable fallback, duplicate detection and end-to-end persistence."""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import AnalysisFailure, ModelUnavailable
from app.services.contract_analysis import ContractAnalysisService, text_hash
from app.services.ml_adapter import ClauseAnalyzer, MLAnalyzerAdapter
from tests.conftest import MockAnalyzer, SAMPLE_CONTRACT_TEXT


@pytest.fixture()
def service(settings: Settings, mock_analyzer) -> ContractAnalysisService:
    return ContractAnalysisService(analyzer=mock_analyzer, settings=settings)


@pytest.fixture()
def ingested(service: ContractAnalysisService, sample_txt) -> dict:
    return service.ingest_document(sample_txt, "sample contract.txt")


class TestIngestion:
    def test_ingest_persists_contract(self, service: ContractAnalysisService, ingested):
        cid = ingested["contract_id"]
        result = service.get_full_result(cid)
        assert result is not None
        assert result["contract"]["filename"] == "sample contract.txt"
        assert result["contract"]["character_count"] > 0
        assert result["contract"]["text"] == SAMPLE_CONTRACT_TEXT  # STORE_RAW_TEXT on

    def test_no_raw_text_when_disabled(self, settings: Settings, sample_txt):
        settings.store_raw_text = False
        svc = ContractAnalysisService(analyzer=MockAnalyzer(), settings=settings)
        ing = svc.ingest_document(sample_txt, "x.txt")
        result = svc.get_full_result(ing["contract_id"])
        assert result["contract"]["text"] == ""

    def test_duplicate_detection(self, service: ContractAnalysisService, sample_txt):
        first = service.ingest_document(sample_txt, "a.txt")
        second = service.ingest_document(sample_txt, "b.txt")
        assert second["duplicate_of"] == first["contract_id"]
        assert second["contract_id"] != first["contract_id"]

    def test_hash_is_stable_and_normalized(self):
        assert text_hash("a  b\nc") == text_hash("a b c")
        assert text_hash("a") != text_hash("b")


class TestAnalysisFlow:
    def test_full_flow_persists_everything(self, service: ContractAnalysisService, ingested):
        result = service.analyze_contract(ingested["contract_id"])
        a = result["analysis"]
        assert a["status"] == "COMPLETED"
        assert a["model_state"] == "fine_tuned"
        # 18 non-compete + 15 exclusivity + 10 auto-renewal + 5 renewal + 8 anti-assignment
        # + 3 anti-assignment base + 10 termination absent + 12 cap absent = 81 -> HIGH
        assert a["overall_risk_score"] == 81
        assert a["overall_risk_level"] == "HIGH"
        assert "not legal advice" in a["disclaimer"] or "reviewed" in a["disclaimer"]

        labels = {c["clause_type"] for c in result["clauses"]}
        assert "governing_law" in labels
        gov = next(c for c in result["clauses"] if c["clause_type"] == "governing_law")
        assert gov["risk_level"] == "INFO"
        nc = next(c for c in result["clauses"] if c["clause_type"] == "non_compete")
        assert nc["risk_level"] == "HIGH"

        rule_ids = {f["rule_id"] for f in result["risk_findings"]}
        assert "NON_COMPETE_PRESENT" in rule_ids
        assert "CAP_ON_LIABILITY_ABSENT" in rule_ids

    def test_reload_persists_after_service_rerun(self, service: ContractAnalysisService, ingested):
        cid = ingested["contract_id"]
        service.analyze_contract(cid)
        # a fresh read (new implicit session) sees the completed analysis
        result = service.get_full_result(cid)
        assert result["analysis"]["status"] == "COMPLETED"
        assert result["contract"]["status"] == "COMPLETED"

    def test_analyze_unknown_contract_fails(self, service: ContractAnalysisService):
        with pytest.raises(AnalysisFailure):
            service.analyze_contract("does-not-exist")

    def test_model_failure_marks_failed(self, settings: Settings, sample_txt):
        svc = ContractAnalysisService(analyzer=MockAnalyzer(fail=True), settings=settings)
        ing = svc.ingest_document(sample_txt, "x.txt")
        with pytest.raises(AnalysisFailure):
            svc.analyze_contract(ing["contract_id"])
        result = svc.get_full_result(ing["contract_id"])
        assert result["analysis"]["status"] == "FAILED"
        assert "model exploded" in result["analysis"]["error_message"]
        assert result["contract"]["status"] == "FAILED"

    def test_failed_analysis_leaves_no_partial_clause_rows(self, settings: Settings, sample_txt):
        svc = ContractAnalysisService(analyzer=MockAnalyzer(fail=True), settings=settings)
        ing = svc.ingest_document(sample_txt, "x.txt")
        with pytest.raises(AnalysisFailure):
            svc.analyze_contract(ing["contract_id"])
        result = svc.get_full_result(ing["contract_id"])
        assert result["clauses"] == [] and result["risk_findings"] == []


class TestModelUnavailable:
    def test_broken_adapter_raises_clean_error(self, settings: Settings, sample_txt):
        class BrokenAdapter:
            def analyze_contract(self, text, enabled_clauses=None):
                raise ModelUnavailable("model files missing")

            def analyze_clause(self, text, label):
                raise ModelUnavailable("model files missing")

        svc = ContractAnalysisService(analyzer=BrokenAdapter(), settings=settings)
        ing = svc.ingest_document(sample_txt, "x.txt")
        with pytest.raises(ModelUnavailable):
            svc.analyze_contract(ing["contract_id"])
        result = svc.get_full_result(ing["contract_id"])
        assert result["analysis"]["status"] == "FAILED"
        assert "model files missing" in result["analysis"]["error_message"]

    def test_adapter_interface_satisfied(self):
        """MockAnalyzer must satisfy the stable ClauseAnalyzer protocol."""
        a: ClauseAnalyzer = MockAnalyzer()
        out = a.analyze_contract("text")
        assert "clauses" in out

    def test_ml_adapter_lazy_without_model(self, settings: Settings):
        """MLAnalyzerAdapter with a missing config raises ModelUnavailable, cleanly."""
        adapter = MLAnalyzerAdapter(settings.temp_dir / "no-such-model.json")
        with pytest.raises(ModelUnavailable):
            _ = adapter.inner
