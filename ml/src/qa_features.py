"""QA feature assembly: training labels, eval metadata, and span decoding.

Training features (extractive QA, CLS-based no-answer handling):
    input_ids, start_position, end_position (+ provenance metadata)
A window whose context slice does not FULLY contain the gold span becomes a
no-answer window (start = end = CLS index) - never an invalid index. This
covers answers outside a window and answers crossing a window boundary.

Multiple gold answers: the official training file explodes each annotated span
into its own QA instance, so every training example carries exactly one gold
span and no information is lost. Evaluation compares a prediction against ALL
gold spans (handled by the metric code in Phase 3).
"""
from __future__ import annotations

from dataclasses import dataclass

from .chunking import WindowFeatures
from .cuad_loader import AnswerSpan, ClauseQA


@dataclass
class TrainFeatures:
    input_ids: list[int]
    start_position: int
    end_position: int
    contract_id: str
    clause_label: str
    qa_id: str
    window_index: int
    is_no_answer: bool
    # original-text char span of the gold answer when the window contains it
    gold_char_span: tuple[int, int] | None


@dataclass
class EvalFeatures:
    """Inference features: enough metadata to decode spans back to the document."""

    input_ids: list[int]
    contract_id: str
    clause_label: str
    qa_id: str
    window_index: int
    # char offsets (into the ORIGINAL contract text) for each context token
    ctx_offsets: list[tuple[int, int]]
    is_no_answer_example: bool  # gold has no span (used only for reporting, never tuning)


def cls_index() -> int:
    return 0  # [CLS] is always the first token of our assembled windows


def token_overlapping_char(
    offsets: list[tuple[int, int]], char_pos: int, search_from: int = 0
) -> int | None:
    """Index of the first token whose char range contains `char_pos`.

    Tokens with zero-width offsets (never present in our context-only slices,
    but guarded anyway) are skipped. Returns None if the char position falls in
    a gap not covered by any token (e.g. whitespace-only spans).
    """
    for i in range(search_from, len(offsets)):
        s, e = offsets[i]
        if e <= s:
            continue
        if s <= char_pos < e:
            return i
        if s > char_pos:
            break
    return None


def answer_token_positions(
    window: WindowFeatures, answer: AnswerSpan
) -> tuple[int, int] | None:
    """Map a gold answer span to (start, end) token positions inside the window.

    Returns None when the window's context slice does not fully contain the
    answer (answer outside the window or crossing a boundary): the caller must
    treat that window as no-answer rather than using clipped indexes.
    """
    if not window.ctx_offsets:
        return None
    win_char_start, win_char_end = window.char_range()
    if answer.start < win_char_start or answer.end > win_char_end:
        return None

    first_ctx = window.ctx_first_token_index_in_window
    local_offsets = window.ctx_offsets

    local_start = token_overlapping_char(local_offsets, answer.start)
    # answer end is exclusive; the token containing the last answer char
    local_end = token_overlapping_char(local_offsets, answer.end - 1)
    if local_start is None or local_end is None:
        return None
    if local_end < local_start:  # defensive; cannot happen with contiguous offsets
        return None
    return first_ctx + local_start, first_ctx + local_end


def build_train_features(
    windows: list[WindowFeatures], qa: ClauseQA
) -> list[TrainFeatures]:
    """Convert sliding windows into training features for one QA instance.

    - no-answer instance (is_impossible): every window targets [CLS]
    - positive instance: windows fully containing the span target its tokens;
      all other windows target [CLS] (outside/boundary-crossing answers)
    """
    features: list[TrainFeatures] = []
    for w in windows:
        span: tuple[int, int] | None = None
        if not qa.is_impossible and qa.answers:
            gold = qa.answers[0]  # training file guarantees one span per instance
            span = answer_token_positions(w, gold)
        if span is None:
            features.append(
                TrainFeatures(
                    input_ids=w.input_ids,
                    start_position=cls_index(),
                    end_position=cls_index(),
                    contract_id=w.contract_id,
                    clause_label=w.clause_label,
                    qa_id=qa.qa_id,
                    window_index=w.window_index,
                    is_no_answer=True,
                    gold_char_span=None,
                )
            )
        else:
            features.append(
                TrainFeatures(
                    input_ids=w.input_ids,
                    start_position=span[0],
                    end_position=span[1],
                    contract_id=w.contract_id,
                    clause_label=w.clause_label,
                    qa_id=qa.qa_id,
                    window_index=w.window_index,
                    is_no_answer=False,
                    gold_char_span=(qa.answers[0].start, qa.answers[0].end),
                )
            )
    return features


def build_eval_features(
    windows: list[WindowFeatures], qa: ClauseQA
) -> list[EvalFeatures]:
    return [
        EvalFeatures(
            input_ids=w.input_ids,
            contract_id=w.contract_id,
            clause_label=w.clause_label,
            qa_id=qa.qa_id,
            window_index=w.window_index,
            ctx_offsets=list(w.ctx_offsets),
            is_no_answer_example=qa.is_impossible,
        )
        for w in windows
    ]


def decode_token_span(
    eval_feature: EvalFeatures, start_token_in_window: int, end_token_in_window: int,
    ctx_first_token_index: int,
) -> tuple[int, int]:
    """Decode predicted token positions to char offsets in the original contract.

    start/end_token_in_window are indexes into input_ids (CLS=0). The caller
    extracts the evidence text from the original context via decode_text(), so
    the UI can highlight exact evidence.
    """
    local_start = start_token_in_window - ctx_first_token_index
    local_end = end_token_in_window - ctx_first_token_index
    if local_start < 0 or local_end >= len(eval_feature.ctx_offsets) or local_end < local_start:
        raise ValueError("Predicted token span is outside the window's context slice.")
    return eval_feature.ctx_offsets[local_start][0], eval_feature.ctx_offsets[local_end][1]


def decode_text(context: str, char_start: int, char_end: int) -> str:
    return context[char_start:char_end]
