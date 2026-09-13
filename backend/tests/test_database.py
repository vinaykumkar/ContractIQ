"""Database layer tests: schema, repository CRUD, rollback, duplicate hash,
project-relative paths and portability overrides."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import PROJECT_ROOT, Settings, load_settings, risk_bands
from app.core.exceptions import DatabaseFailure
from app.db.database import get_engine, init_db, make_session_factory, session_scope
from app.db import repository as repo


@pytest.fixture()
def db(settings: Settings):
    engine = get_engine(settings.database_url)
    init_db(engine)
    factory = make_session_factory(engine)
    yield factory
    engine.dispose()


def _mk_contract(session, cid="C1", h=None):
    return repo.create_contract(
        session, contract_id=cid, filename="c.pdf", original_filename="c.pdf",
        file_type="pdf", character_count=100, page_count=2, text_hash=h or f"hash-{cid}",
    )


class TestSchemaAndPersistence:
    def test_init_db_creates_tables(self, db):
        from sqlalchemy import inspect

        with session_scope(db) as s:
            names = set(inspect(s.bind).get_table_names())
        assert {"contracts", "analyses", "clause_results", "risk_findings"} <= names

    def test_contract_roundtrip(self, db):
        with session_scope(db) as s:
            _mk_contract(s)
            c = repo.get_contract(s, "C1")
            assert c is not None and c.filename == "c.pdf" and c.status == "UPLOADED"
        with session_scope(db) as s:  # new session: committed
            assert repo.get_contract(s, "C1") is not None

    def test_analysis_persistence_chain(self, db):
        with session_scope(db) as s:
            _mk_contract(s)
            a = repo.create_analysis(s, contract_id="C1", model_state="fine_tuned",
                                     model_version="test")
            repo.save_clause_results(s, a.id, [
                {"clause_type": "governing_law", "found": True, "text": "NY law",
                 "confidence": 0.9, "start_char": 5, "end_char": 10,
                 "risk_level": "INFO", "risk_reason": "info"},
                {"clause_type": "non_compete", "found": False, "text": "",
                 "confidence": 0.1},
            ])
            repo.save_risk_findings(s, a.id, [
                {"rule_id": "NON_COMPETE_PRESENT", "clause_type": "non_compete",
                 "severity": "HIGH", "weight": 18, "reason": "r", "evidence": "e",
                 "confidence": 0.9, "uncertain": False},
            ])
            repo.complete_analysis(s, a, processing_ms=12.5,
                                   overall_risk_score=18, overall_risk_level="MEDIUM")
        with session_scope(db) as s:
            got = repo.get_analysis(s, a.id)
            assert got.status == "COMPLETED"
            assert got.overall_risk_level == "MEDIUM"
            assert len(got.clause_results) == 2
            assert len(got.risk_findings) == 1
            assert got.clause_results[0].found == 1
            assert got.clause_results[1].found == 0

    def test_latest_analysis_and_list(self, db):
        with session_scope(db) as s:
            _mk_contract(s, "C1")
            for lvl in ("LOW", "HIGH"):
                a = repo.create_analysis(s, contract_id="C1")
                repo.complete_analysis(s, a, overall_risk_level=lvl)
        with session_scope(db) as s:
            assert repo.latest_analysis(s, "C1").overall_risk_level == "HIGH"
            highs, total = repo.list_contracts(s, risk_level="HIGH")
            assert total == 1 and [c.id for c in highs] == ["C1"]

    def test_delete_contract_cascades(self, db):
        with session_scope(db) as s:
            _mk_contract(s)
            a = repo.create_analysis(s, contract_id="C1")
            repo.save_clause_results(s, a.id, [
                {"clause_type": "x", "found": False}])
        with session_scope(db) as s:
            assert repo.delete_contract(s, "C1") is True
        with session_scope(db) as s:
            assert repo.get_contract(s, "C1") is None
            assert repo.analyses_for_contract(s, "C1") == []


class TestRollback:
    def test_failure_mid_transaction_leaves_no_rows(self, db):
        with pytest.raises(RuntimeError):
            with session_scope(db) as s:
                _mk_contract(s, "C1")
                raise RuntimeError("boom mid-transaction")
        with session_scope(db) as s:
            assert repo.get_contract(s, "C1") is None

    def test_failure_after_analysis_partial_write_rolls_back(self, db):
        with session_scope(db) as s:
            _mk_contract(s, "C2")
        with pytest.raises(ValueError):
            with session_scope(db) as s:
                a = repo.create_analysis(s, contract_id="C2")
                repo.save_clause_results(s, a.id, [
                    {"clause_type": "x", "found": False}])
                raise ValueError("simulated persistence error")
        with session_scope(db) as s:
            # analysis + clause rows were never committed
            assert repo.analyses_for_contract(s, "C2") == []


class TestDuplicateHash:
    def test_find_by_hash(self, db):
        with session_scope(db) as s:
            _mk_contract(s, "C1", h="abc123")
        with session_scope(db) as s:
            found = repo.find_contract_by_hash(s, "abc123")
            assert found is not None and found.id == "C1"
            assert repo.find_contract_by_hash(s, "nope") is None
            assert repo.find_contract_by_hash(s, "") is None


class TestPortabilityAndConfig:
    def test_default_db_path_is_project_relative(self):
        s = load_settings()
        assert s.database_url.startswith("sqlite:///")
        db_file = s.database_url.replace("sqlite:///", "")
        assert Path(db_file).is_absolute()  # resolved, not a hardcoded literal
        assert PROJECT_ROOT.as_posix() in Path(db_file).as_posix()
        assert Path(db_file).name == "contractiq.db"

    def test_env_override_db_url(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONTRACTIQ_DB_URL", f"sqlite:///{(tmp_path / 'other.db').as_posix()}")
        s = load_settings()
        assert "other.db" in s.database_url

    def test_env_override_dirs_and_flags(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CONTRACTIQ_UPLOAD_DIR", str(tmp_path / "up"))
        monkeypatch.setenv("CONTRACTIQ_STORE_RAW_TEXT", "false")
        monkeypatch.setenv("CONTRACTIQ_RISK_MIN_CONFIDENCE", "0.7")
        s = load_settings()
        assert s.upload_dir == (tmp_path / "up").resolve()
        assert s.store_raw_text is False
        assert s.risk_min_confidence == 0.7

    def test_settings_do_not_contain_hardcoded_paths(self):
        """The settings module itself must not embed any absolute machine path.

        (At runtime the DB path is RESOLVED from PROJECT_ROOT, which is by
        design - here we verify the source has no hardcoded literal.)
        """
        import inspect

        from app.core import config as cfg_module

        source = inspect.getsource(cfg_module)
        forbidden = "C:" + chr(92) + "proj2"  # avoid the literal in this test file
        assert forbidden not in source and forbidden.replace(chr(92), "/") not in source
        # and the default path is relative before resolution
        assert not cfg_module._resolve("storage/contractiq.db").is_relative_to(Path("storage"))

    def test_risk_bands_from_registry(self):
        bands = risk_bands()
        assert bands == {"low_max": 30, "medium_max": 60}

    def test_bad_db_url_raises_domain_error(self):
        with pytest.raises(DatabaseFailure):
            get_engine("not-a-valid-url://x")
