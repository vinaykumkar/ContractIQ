"""Tests for token-level sliding-window chunking and question budget."""
from __future__ import annotations

import pytest

from ml.src.chunking import (
    ChunkingError,
    build_windows_for_clause,
    tokenize_context,
    validate_window_fit,
    window_token_ranges,
)

from conftest import make_clause, synthetic_record


def test_window_ranges_coverage_and_overlap():
    ranges = window_token_ranges(n_ctx_tokens=200, max_ctx_tokens=56, doc_stride=16)
    assert ranges[0] == (0, 56)
    # consecutive windows advance by stride
    for (s1, _), (s2, _) in zip(ranges, ranges[1:]):
        assert s2 - s1 == 56 - 16
    # full coverage
    assert ranges[-1][1] == 200
    for i in range(200):
        assert any(s <= i < e for s, e in ranges)


def test_window_ranges_single_and_empty():
    assert window_token_ranges(10, 56, 16) == [(0, 10)]
    assert window_token_ranges(0, 56, 16) == []


def test_window_ranges_rejects_degenerate_stride():
    with pytest.raises(ChunkingError):
        window_token_ranges(100, 56, 56)


def test_long_contract_produces_multiple_windows(tokenizer, small_config):
    record = synthetic_record(n_words=120)  # 120 tokens > max_ctx (64 - q - 3)
    tokenized = tokenize_context(tokenizer, record)
    clause = make_clause()
    q_ids = tokenizer(clause.question, add_special_tokens=False)["input_ids"]
    windows = build_windows_for_clause(
        tokenized, q_ids, clause.label, small_config,
        tokenizer.cls_token_id, tokenizer.sep_token_id,
    )
    assert len(windows) > 1
    expected = window_token_ranges(len(tokenized.token_ids),
                                   small_config.max_seq_len - len(q_ids) - 3,
                                   small_config.doc_stride)
    assert len(windows) == len(expected)
    # every window has the right input_ids layout: [CLS] q [SEP] ctx [SEP]
    for w in windows:
        assert w.input_ids[0] == tokenizer.cls_token_id
        assert w.input_ids[-1] == tokenizer.sep_token_id
        assert w.input_ids[1:1 + len(q_ids)] == q_ids
        assert w.input_ids[1 + len(q_ids)] == tokenizer.sep_token_id
        assert len(w.input_ids) == len(q_ids) + 3 + (w.ctx_token_end - w.ctx_token_start)
        assert len(w.ctx_offsets) == w.ctx_token_end - w.ctx_token_start


def test_offsets_map_back_to_original_text(tokenizer):
    record = synthetic_record(n_words=50, answer_words=(10, 12))
    tokenized = tokenize_context(tokenizer, record)
    for tok_id, (s, e) in zip(tokenized.token_ids, tokenized.offsets):
        assert 0 <= s < e <= len(record.context)
        piece = tokenizer.convert_ids_to_tokens(int(tok_id))
        # single-letter words: offsets must slice exactly that word
        assert record.context[s:e] == piece.replace("##", "") or piece.startswith("##")


def test_question_is_never_truncated(tokenizer, small_config):
    """Truncation must only ever hit the context: window layout proves it."""
    record = synthetic_record(n_words=150)
    tokenized = tokenize_context(tokenizer, record)
    clause = make_clause()
    q_ids = tokenizer(clause.question, add_special_tokens=False)["input_ids"]
    windows = build_windows_for_clause(
        tokenized, q_ids, clause.label, small_config,
        tokenizer.cls_token_id, tokenizer.sep_token_id,
    )
    for w in windows:
        assert w.question_token_len == len(q_ids)
        assert w.input_ids[1:1 + len(q_ids)] == q_ids


def test_overlong_question_fails_loudly(tokenizer, small_config):
    long_question = "word " * small_config.max_seq_len
    with pytest.raises(ChunkingError, match="never|truncated|fit"):
        validate_window_fit(small_config, tokenizer, long_question, "test_clause")


def test_validate_window_fit_returns_q_len(tokenizer, small_config):
    clause = make_clause()
    n = validate_window_fit(small_config, tokenizer, clause.question, clause.label)
    assert n == len(tokenizer(clause.question, add_special_tokens=False)["input_ids"])
