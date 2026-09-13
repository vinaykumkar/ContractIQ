"""Tests for CUAD loading, answer validation, and the untouched test set."""
from __future__ import annotations

import hashlib
import json

import pytest

from ml.src import config as cfg
from ml.src.cuad_loader import (
    AnswerSpan,
    ClauseQA,
    ContractRecord,
    CuadDataError,
    load_contracts,
    load_test_contracts,
    load_train_contracts,
    validate_answer,
)

from conftest import make_clause

MINIMAL_CLAUSES = [make_clause("governing_law", "Governing Law"), make_clause("parties", "Parties")]


def _write_mini_cuad(path, contract_id="C1", context="Governing law is Delaware. Signed by A and B.",
                     answers=None, is_impossible=False, category="Governing Law"):
    payload = {
        "version": "aok_v1.0",
        "data": [{
            "title": contract_id,
            "paragraphs": [{
                "context": context,
                "qas": [{
                    "question": f'Highlight the parts (if any) of this contract related to "{category}" that should be reviewed by a lawyer. Details: test',
                    "id": f"{contract_id}__{category}",
                    "is_impossible": is_impossible,
                    "answers": answers if answers is not None else [],
                }],
            }],
        }],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_load_synthetic_cuad_strict(tmp_path):
    path = tmp_path / "mini.json"
    _write_mini_cuad(path, answers=[{"text": "Delaware", "answer_start": 17}])
    records = load_contracts(path, MINIMAL_CLAUSES, strict=True)
    assert len(records) == 1
    rec = records[0]
    assert rec.contract_id == "C1"
    assert len(rec.qas) == 1
    qa = rec.qas[0]
    assert qa.clause_label == "governing_law"
    assert qa.cuad_category == "Governing Law"
    assert qa.answers[0].text == "Delaware"


def test_malformed_answer_detected_and_raised(tmp_path):
    path = tmp_path / "mini.json"
    # offset off by one - must NOT be silently repaired
    _write_mini_cuad(path, answers=[{"text": "Delaware", "answer_start": 19}])
    with pytest.raises(CuadDataError, match="mismatch"):
        load_contracts(path, MINIMAL_CLAUSES, strict=True)


def test_out_of_bounds_answer_detected(tmp_path):
    path = tmp_path / "mini.json"
    _write_mini_cuad(path, answers=[{"text": "Delaware.", "answer_start": 100}])
    with pytest.raises(CuadDataError, match="out of bounds"):
        load_contracts(path, MINIMAL_CLAUSES, strict=True)


def test_impossible_with_answers_detected(tmp_path):
    path = tmp_path / "mini.json"
    _write_mini_cuad(path, answers=[{"text": "Delaware", "answer_start": 18}], is_impossible=True)
    with pytest.raises(CuadDataError, match="impossible"):
        load_contracts(path, MINIMAL_CLAUSES, strict=True)


def test_duplicate_contract_titles_detected(tmp_path):
    payload = {
        "version": "aok_v1.0",
        "data": [
            {"title": "DUP", "paragraphs": [{"context": "x", "qas": []}]},
            {"title": "DUP", "paragraphs": [{"context": "y", "qas": []}]},
        ],
    }
    path2 = tmp_path / "dup.json"
    path2.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CuadDataError, match="Duplicate"):
        load_contracts(path2, MINIMAL_CLAUSES, strict=False)


def test_real_train_file_loads_strict():
    """Load first 3 contracts of the real training file with strict validation."""
    records = load_train_contracts(MINIMAL_CLAUSES, limit=3, strict=True)
    assert len(records) == 3
    for rec in records:
        assert rec.contract_id
        assert rec.context
        for qa in rec.qas:
            assert qa.clause_label in {"governing_law", "parties"}
            if qa.is_impossible:
                assert not qa.answers


def test_official_test_set_remains_untouched():
    """Loading must not modify the file; hashing before/after proves it."""
    before = hashlib.sha256(cfg.TEST_PATH.read_bytes()).hexdigest()
    records = load_test_contracts(MINIMAL_CLAUSES, limit=2, strict=True)
    after = hashlib.sha256(cfg.TEST_PATH.read_bytes()).hexdigest()
    assert before == after
    assert len(records) == 2


def test_validate_answer_unit():
    validate_answer("hello world", AnswerSpan("world", 6), "c", "q")  # ok
    with pytest.raises(CuadDataError):
        validate_answer("hello world", AnswerSpan("wor ld", 6), "c", "q")
