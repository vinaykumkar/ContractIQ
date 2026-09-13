"""Tests for the answer decoder: span validity, CLS scoring, decision rules."""
from __future__ import annotations

import math

import pytest
import torch

from ml.src.decoder import decode_window, decision_to_dict, decide_clause


def logits_with_peak(n=64, start=10, end=14, peak=12.0):
    s = torch.zeros(n)
    e = torch.zeros(n)
    s[start] = peak
    e[end] = peak
    return s, e


def test_decode_window_finds_peak_span():
    s, e = logits_with_peak(n=64, start=10, end=14)
    p = decode_window(s, e, ctx_from=1, ctx_to=63, max_answer_tokens=8)
    assert p.start_token == 10 and p.end_token == 14
    conf = float(torch.softmax(s, -1)[10] * torch.softmax(e, -1)[14])
    assert abs(p.span_confidence - conf) < 1e-6
    assert 0 < p.span_confidence <= 1.0
    assert 0 < p.cls_confidence <= 1.0


def test_decode_window_respects_context_slice():
    s, e = logits_with_peak(n=64, start=10, end=14, peak=12.0)
    # peak outside the context slice (question zone 0..5) must be ignored
    p = decode_window(s, e, ctx_from=20, ctx_to=60, max_answer_tokens=8)
    assert p.start_token >= 20 and p.end_token < 60


def test_decode_window_enforces_max_answer_length():
    s = torch.zeros(64)
    e = torch.zeros(64)
    s[5] = 6.0
    e[30] = 6.0  # span of 26 tokens > max 8
    p = decode_window(s, e, ctx_from=1, ctx_to=63, max_answer_tokens=8)
    assert p.end_token - p.start_token < 8


def test_decode_window_vectorized_matches_bruteforce():
    """The tensorized span search must equal a sequential first-max scan."""
    g = torch.Generator().manual_seed(7)
    s = torch.randn(96, generator=g)
    e = torch.randn(96, generator=g)
    ctx_from, ctx_to, max_len = 6, 90, 12

    p = decode_window(s, e, ctx_from, ctx_to, max_len)
    sm = torch.softmax(s.float(), -1)
    em = torch.softmax(e.float(), -1)
    best = (ctx_from, ctx_from, -1.0)
    for i in range(ctx_from, ctx_to):
        for j in range(i, min(i + max_len, ctx_to)):
            score = float(sm[i] * em[j])
            if score > best[2]:
                best = (i, j, score)
    assert p.start_token == best[0] and p.end_token == best[1]
    assert abs(p.span_confidence - best[2]) < 1e-6


def test_decode_window_cls_score_is_zero_token_product():
    s, e = logits_with_peak(n=64)
    p = decode_window(s, e, ctx_from=1, ctx_to=63, max_answer_tokens=8)
    expected = float(torch.softmax(s, -1)[0] * torch.softmax(e, -1)[0])
    assert abs(p.cls_confidence - expected) < 1e-7


def _decide(preds, context, delta=0.1, min_conf=0.05, start=3, end=8):
    return decide_clause("test_clause", preds, context, start, end, delta, min_conf)


def test_decide_found_when_span_dominates_cls():
    preds = [WindowPrediction(0, 3, 8, 0.9, 0.05)]
    d = _decide(preds, "some contract text")
    assert d.found is True
    assert d.text == "some contract text"[3:8]
    assert d.start_char == 3 and d.end_char == 8


def test_decide_no_answer_when_margin_too_small():
    preds = [WindowPrediction(0, 3, 8, 0.9, 0.85)]
    d = _decide(preds, "some contract text", delta=0.1)
    assert d.found is False and d.text == ""


def test_decide_no_answer_when_below_min_confidence():
    preds = [WindowPrediction(0, 3, 8, 0.02, 0.0)]
    d = _decide(preds, "some contract text", min_conf=0.05)
    assert d.found is False


def test_decide_best_span_across_windows():
    preds = [
        WindowPrediction(0, 3, 8, 0.30, 0.10),
        WindowPrediction(1, 2, 9, 0.75, 0.20),
        WindowPrediction(2, 4, 4, 0.50, 0.60),
    ]
    d = _decide(preds, "some contract text long enough", delta=0.1, min_conf=0.05,
                start=5, end=20)
    assert d.found is True
    assert d.confidence == 0.75
    assert d.no_answer_score == 0.60  # max cls across windows
    assert d.windows_considered == 3


def test_decide_empty_predictions_is_no_answer():
    d = _decide([], "text")
    assert d.found is False and d.windows_considered == 0


def test_decide_rejects_offsets_outside_context():
    preds = [WindowPrediction(0, 3, 8, 0.9, 0.05)]
    with pytest.raises(ValueError):
        _decide(preds, "short", start=50, end=90)


def test_decision_to_dict_shape():
    preds = [WindowPrediction(0, 3, 8, 0.9, 0.05)]
    d = _decide(preds, "some contract text")
    out = decision_to_dict(d)
    assert out["clause_type"] == "test_clause"
    assert out["found"] is True
    assert out["confidence"] == 0.9
    assert out["text"] == "some contract text"[3:8]


from ml.src.decoder import WindowPrediction  # noqa: E402  (used above)
