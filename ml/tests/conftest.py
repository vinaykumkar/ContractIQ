"""Shared fixtures for ContractIQ ML tests.

Uses the cached distilbert-base-uncased tokenizer (downloaded on first run)
and small synthetic contracts for fast, deterministic window/label tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.src.config import ClauseSpec, WindowConfig  # noqa: E402


@pytest.fixture(scope="session")
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained("distilbert-base-uncased", use_fast=True)


@pytest.fixture(scope="session")
def real_config() -> WindowConfig:
    return WindowConfig(
        max_seq_len=512,
        doc_stride=128,
        max_answer_tokens=64,
        no_answer_threshold=0.35,
        min_confidence=0.25,
    )


@pytest.fixture(scope="session")
def small_config() -> WindowConfig:
    """Small window config so synthetic contexts produce multiple windows fast."""
    return WindowConfig(
        max_seq_len=64,
        doc_stride=16,
        max_answer_tokens=8,
        no_answer_threshold=0.35,
        min_confidence=0.25,
    )


def make_clause(label: str = "test_clause", category: str = "Test Category") -> ClauseSpec:
    question = (
        f'Highlight the parts (if any) of this contract related to "{category}" '
        "that should be reviewed by a lawyer. Details: test"
    )
    return ClauseSpec(label=label, cuad_category=category, question=question, enabled=True)


def synthetic_record(
    n_words: int = 120,
    answer_words: tuple[int, int] | None = None,  # inclusive word range
    word: str = "alpha",
    contract_id: str = "TEST_CONTRACT",
):
    """Build a synthetic contract of single-token words.

    Words are lowercase letters separated by single spaces, so each word is
    exactly one WordPiece token with char offsets [2*i, 2*i+1).
    """
    from ml.src.cuad_loader import AnswerSpan, ClauseQA, ContractRecord

    words = [chr(ord("a") + (i % 26)) for i in range(n_words)]
    context = " ".join(words)
    qas = []
    if answer_words is not None:
        s, e = answer_words
        text = context[s * 2 : e * 2 + 1]
        qas.append(
            ClauseQA(
                clause_label="test_clause",
                cuad_category="Test Category",
                question=make_clause().question,
                answers=[AnswerSpan(text=text, start=s * 2)],
                is_impossible=False,
                qa_id=f"{contract_id}__Test Category_0",
            )
        )
    else:
        qas.append(
            ClauseQA(
                clause_label="test_clause",
                cuad_category="Test Category",
                question=make_clause().question,
                answers=[],
                is_impossible=True,
                qa_id=f"{contract_id}__Test Category_0",
            )
        )
    return ContractRecord(contract_id=contract_id, context=context, qas=qas)
