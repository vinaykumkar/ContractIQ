"""Answer decoding: window logits -> span decision with no-answer handling.

Pure functions over logits so they are cheap to unit-test. The decision rule:

- per window: best span inside the context slice (start<=end, length<=max),
  scored p_start * p_end (softmax over the WHOLE window so [CLS] competes)
- the [CLS]/[CLS] product is the window's no-answer score
- across windows: best span wins by confidence; clause no-answer score is the
  max [CLS] score
- found iff (span_confidence - cls_confidence) >= no_answer_delta AND
  span_confidence >= min_confidence

Both thresholds are calibrated on the validation split (never on the official
test set) and stored in ml/configs/model.json. Decoded text is always an exact
substring of the original contract context - nothing is fabricated.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class WindowPrediction:
    window_index: int
    start_token: int  # index into input_ids
    end_token: int
    span_confidence: float  # p_start * p_end, in (0, 1]
    cls_confidence: float  # p_cls_start * p_cls_end, in (0, 1]


@dataclass(frozen=True)
class ClauseDecision:
    clause_label: str
    found: bool
    text: str
    confidence: float
    start_char: int
    end_char: int
    no_answer_score: float
    window_index: int | None
    windows_considered: int


def decode_window(
    start_logits: torch.Tensor,
    end_logits: torch.Tensor,
    ctx_from: int,
    ctx_to: int,
    max_answer_tokens: int,
    window_index: int = 0,
) -> WindowPrediction:
    """Best valid span + CLS score for one window's logits.

    Vectorized: the (start, end) score matrix p_start[i] * p_end[j] is computed
    with tensor ops over the context slice; spans violating j>=i or
    j-i<max_answer_tokens are masked. Ties resolve to the lowest (i, j),
    matching a sequential first-max scan. Invalid spans (outside the context
    slice, start>end, oversized) are never returned.
    """
    s = torch.softmax(start_logits.float(), dim=-1)
    e = torch.softmax(end_logits.float(), dim=-1)
    cls_confidence = float(s[0] * e[0])

    n = ctx_to - ctx_from
    if n <= 0:
        return WindowPrediction(window_index=window_index, start_token=max(ctx_from, 0),
                                end_token=max(ctx_from, 0), span_confidence=0.0,
                                cls_confidence=cls_confidence)
    s_c = s[ctx_from:ctx_to]
    e_c = e[ctx_from:ctx_to]
    scores = s_c.unsqueeze(1) * e_c.unsqueeze(0)  # scores[i, j] = p_s[i] * p_e[j]
    idx = torch.arange(n, device=scores.device)
    invalid = (idx.unsqueeze(0) - idx.unsqueeze(1)) < 0  # j < i
    invalid |= (idx.unsqueeze(0) - idx.unsqueeze(1)) >= max_answer_tokens  # oversized
    scores = scores.masked_fill(invalid, -1.0)
    flat_best = int(scores.flatten().argmax())
    best_i, best_j = divmod(flat_best, n)
    return WindowPrediction(
        window_index=window_index,
        start_token=ctx_from + best_i,
        end_token=ctx_from + best_j,
        span_confidence=max(float(scores[best_i, best_j]), 0.0),
        cls_confidence=cls_confidence,
    )


def decide_clause(
    clause_label: str,
    predictions: list[WindowPrediction],
    context: str,
    start_char_offset: int,
    end_char_offset: int,
    no_answer_delta: float,
    min_confidence: float,
) -> ClauseDecision:
    """Combine window predictions into one clause decision.

    start_char_offset/end_char_offset are the char spans of the winning
    window's start/end tokens in the ORIGINAL context. The returned text is the
    exact original-context substring; when no window exists or the decision is
    no-answer, found=False and text is empty.
    """
    if not predictions:
        return ClauseDecision(clause_label=clause_label, found=False, text="",
                              confidence=0.0, start_char=-1, end_char=-1,
                              no_answer_score=0.0, window_index=None, windows_considered=0)
    best_span = max(predictions, key=lambda p: p.span_confidence)
    cls_score = max(p.cls_confidence for p in predictions)
    found = (
        best_span.span_confidence >= min_confidence
        and (best_span.span_confidence - cls_score) >= no_answer_delta
    )
    if not found:
        return ClauseDecision(
            clause_label=clause_label, found=False, text="",
            confidence=round(best_span.span_confidence, 6),
            start_char=-1, end_char=-1, no_answer_score=round(cls_score, 6),
            window_index=best_span.window_index, windows_considered=len(predictions),
        )
    if start_char_offset < 0 or end_char_offset > len(context) or start_char_offset > end_char_offset:
        raise ValueError("Decoded char offsets fall outside the original context.")
    return ClauseDecision(
        clause_label=clause_label,
        found=True,
        text=context[start_char_offset:end_char_offset],
        confidence=round(best_span.span_confidence, 6),
        start_char=start_char_offset,
        end_char=end_char_offset,
        no_answer_score=round(cls_score, 6),
        window_index=best_span.window_index,
        windows_considered=len(predictions),
    )


def decision_to_dict(d: ClauseDecision) -> dict:
    return {
        "clause_type": d.clause_label,
        "found": d.found,
        "text": d.text if d.found else "",
        "confidence": d.confidence,
        "start_char": d.start_char,
        "end_char": d.end_char,
        "no_answer_score": d.no_answer_score,
        "windows_considered": d.windows_considered,
    }
