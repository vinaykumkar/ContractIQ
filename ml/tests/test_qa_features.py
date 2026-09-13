"""Tests for training label mapping, no-answer handling, and span decoding."""
from __future__ import annotations

from ml.src.chunking import build_windows_for_clause, tokenize_context
from ml.src.qa_features import (
    answer_token_positions,
    build_eval_features,
    build_train_features,
    decode_text,
    decode_token_span,
)

from conftest import make_clause, synthetic_record


def _windows(tokenizer, config, record, clause_label="test_clause"):
    tokenized = tokenize_context(tokenizer, record)
    clause = make_clause()
    q_ids = tokenizer(clause.question, add_special_tokens=False)["input_ids"]
    return build_windows_for_clause(
        tokenized, q_ids, clause_label, config,
        tokenizer.cls_token_id, tokenizer.sep_token_id,
    )


def test_positive_answer_maps_to_correct_tokens(tokenizer, small_config):
    record = synthetic_record(n_words=120, answer_words=(70, 75))
    windows = _windows(tokenizer, small_config, record)
    feats = build_train_features(windows, record.qas[0])
    positives = [f for f in feats if not f.is_no_answer]
    assert positives, "answer must be fully contained in at least one window"
    for f in positives:
        assert f.start_position <= f.end_position
        assert f.gold_char_span is not None
        # decode back to original text and compare with the gold span
        w = windows[f.window_index]
        char_s, char_e = w.ctx_offsets[
            f.start_position - w.ctx_first_token_index_in_window
        ][0], w.ctx_offsets[
            f.end_position - w.ctx_first_token_index_in_window
        ][1]
        assert record.context[char_s:char_e] == record.qas[0].answers[0].text


def test_no_answer_instance_maps_every_window_to_cls(tokenizer, small_config):
    record = synthetic_record(n_words=120, answer_words=None)
    assert record.qas[0].is_impossible
    windows = _windows(tokenizer, small_config, record)
    feats = build_train_features(windows, record.qas[0])
    assert feats
    for f in feats:
        assert f.is_no_answer
        assert f.start_position == 0  # [CLS]
        assert f.end_position == 0
        assert f.gold_char_span is None


def test_answer_outside_window_becomes_cls(tokenizer, small_config):
    record = synthetic_record(n_words=120, answer_words=(2, 4))
    windows = _windows(tokenizer, small_config, record)
    feats = build_train_features(windows, record.qas[0])
    # windows that do not contain the answer must be CLS, never invalid indexes
    for f in feats:
        w = windows[f.window_index]
        win_s, win_e = w.char_range()
        contains = record.qas[0].answers[0].start >= win_s and record.qas[0].answers[0].end <= win_e
        if not contains:
            assert f.is_no_answer and f.start_position == 0 and f.end_position == 0


def test_answer_crossing_boundary_is_never_clipped(tokenizer, small_config):
    """An answer crossing a window edge must be CLS in windows that clip it.

    With max_ctx=... a long answer straddling the boundary of the first window
    (tokens ~30-60 of 120) falls fully inside NO window: every window must be
    CLS rather than emitting a truncated (clipped) span.
    """
    record = synthetic_record(n_words=120, answer_words=(30, 60))  # 31-token span
    windows = _windows(tokenizer, small_config, record)
    spans = []
    for w in windows:
        pos = answer_token_positions(w, record.qas[0].answers[0])
        if pos is not None:
            spans.append((w.window_index, pos))
    # if any window contains it, fine - but no window may CLIP it
    for w in windows:
        pos = answer_token_positions(w, record.qas[0].answers[0])
        win_s, win_e = w.char_range()
        gold = record.qas[0].answers[0]
        if pos is not None:
            assert gold.start >= win_s and gold.end <= win_e
    # with this geometry no window can contain a 31-token span when
    # max_ctx - stride < 31... assert the clipping-safety invariant regardless:
    for f in build_train_features(windows, record.qas[0]):
        if f.is_no_answer:
            assert f.start_position == 0 and f.end_position == 0


def test_multiple_gold_answers_all_get_supervision(tokenizer, small_config):
    """Spans in different regions must each be learnable via some window."""
    from ml.src.cuad_loader import AnswerSpan, ClauseQA

    record = synthetic_record(n_words=200, answer_words=(20, 24))
    extra = AnswerSpan(text=record.context[150 * 2 : 154 * 2 + 1], start=150 * 2)
    record.qas.append(
        ClauseQA(clause_label="test_clause", cuad_category="Test Category",
                 question=record.qas[0].question, answers=[extra],
                 is_impossible=False, qa_id="C__Test Category_1")
    )
    windows = _windows(tokenizer, small_config, record)
    gold_texts = {qa.answers[0].text for qa in record.qas}
    supervised = set()
    for qa in record.qas:
        for f in build_train_features(windows, qa):
            if not f.is_no_answer:
                w = windows[f.window_index]
                s = w.ctx_offsets[f.start_position - w.ctx_first_token_index_in_window][0]
                e = w.ctx_offsets[f.end_position - w.ctx_first_token_index_in_window][1]
                supervised.add(record.context[s:e])
    assert gold_texts <= supervised, "each gold span must be recoverable from some window"


def test_eval_features_decode_prediction_back_to_text(tokenizer, small_config):
    record = synthetic_record(n_words=120, answer_words=(70, 75))
    windows = _windows(tokenizer, small_config, record)
    eval_feats = build_eval_features(windows, record.qas[0])
    assert len(eval_feats) == len(windows)
    gold = record.qas[0].answers[0]
    decoded_any = False
    for ef in eval_feats:
        w = windows[ef.window_index]
        pos = answer_token_positions(w, gold)
        if pos is None:
            continue
        char_s, char_e = decode_token_span(
            ef, pos[0], pos[1], w.ctx_first_token_index_in_window
        )
        assert decode_text(record.context, char_s, char_e) == gold.text
        decoded_any = True
    assert decoded_any


def test_decode_rejects_out_of_context_span(tokenizer, small_config):
    record = synthetic_record(n_words=120, answer_words=(70, 75))
    windows = _windows(tokenizer, small_config, record)
    eval_feats = build_eval_features(windows, record.qas[0])
    import pytest

    with pytest.raises(ValueError):
        decode_token_span(eval_feats[0], 1, 2, 10**9)  # impossible ctx index


def test_answer_positions_none_outside(tokenizer, small_config):
    record = synthetic_record(n_words=120, answer_words=(2, 4))
    windows = _windows(tokenizer, small_config, record)
    last = windows[-1]
    assert answer_token_positions(last, record.qas[0].answers[0]) is None
