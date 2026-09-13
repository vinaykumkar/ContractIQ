"""Tests for the central clause registry and window configuration."""
from __future__ import annotations

import json

import pytest

from ml.src.config import (
    CLAUSE_REGISTRY_PATH,
    ConfigError,
    WindowConfig,
    load_enabled_clauses,
    load_window_config,
)

EXPECTED_V1_LABELS = {
    "document_name", "parties", "agreement_date", "effective_date",
    "expiration_date", "renewal_term", "governing_law",
    "termination_for_convenience", "non_compete", "exclusivity",
    "anti_assignment", "license_grant", "audit_rights", "cap_on_liability",
    "insurance",
}


def test_registry_loads_with_15_enabled_clauses():
    clauses = load_enabled_clauses()
    assert len(clauses) == 15
    assert {c.label for c in clauses} == EXPECTED_V1_LABELS
    assert all(c.enabled for c in clauses)
    assert all(c.question.startswith("Highlight the parts") for c in clauses)


def test_registry_enabled_labels_map_to_actual_cuad_categories():
    """Enabled labels must map to categories that exist in the real dataset."""
    registry = json.loads(CLAUSE_REGISTRY_PATH.read_text(encoding="utf-8"))
    from ml.src.config import CUADV1_PATH
    import re

    cat_re = re.compile(r'related to "(.+?)" that should be reviewed')
    with CUADV1_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    real_categories = {
        m.group(1)
        for item in payload["data"]
        for qa in item["paragraphs"][0]["qas"]
        if (m := cat_re.search(qa["question"]))
    }
    enabled_categories = {c["cuad_category"] for c in registry["clauses"] if c["enabled"]}
    assert enabled_categories <= real_categories


def test_window_config_from_registry(real_config):
    cfg = load_window_config()
    assert cfg == real_config


def test_window_config_rejects_bad_stride():
    with pytest.raises(ConfigError):
        WindowConfig(max_seq_len=512, doc_stride=600, max_answer_tokens=64,
                     no_answer_threshold=0.35, min_confidence=0.25)


def test_window_config_checks_tokenizer_limit(real_config, tokenizer):
    # distilbert reports 512 - the real config must be compatible
    real_config.check_tokenizer_compat(tokenizer.model_max_length)
    # and an oversized window must fail loudly
    with pytest.raises(ConfigError):
        real_config.check_tokenizer_compat(256)
