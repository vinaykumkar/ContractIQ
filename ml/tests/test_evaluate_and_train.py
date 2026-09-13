"""Tests for evaluation metrics and the sampling/collate pieces of training."""
from __future__ import annotations

from ml.src.evaluate import (
    exact_match,
    normalize_answer,
    score_prediction_set,
    sweep_thresholds,
    token_f1,
)


def test_normalize_answer_standard_behaviour():
    assert normalize_answer("The  Agreement!!") == "agreement"
    # official SQuAD removes punctuation without inserting spaces
    assert normalize_answer("A-B C.") == "ab c"
    assert normalize_answer("  The quick   Brown Fox ") == "quick brown fox"


def test_token_f1_and_exact_match():
    f1, p, r = token_f1("the governing law of delaware", "governing law of delaware")
    assert f1 == 1.0 and p == 1.0 and r == 1.0  # only article removed on both sides
    f1, p, r = token_f1("governing law", "governing law of delaware")
    assert 0 < f1 < 1 and p == 1.0 and r < 1.0
    assert exact_match("The Agreement", "agreement")
    assert not exact_match("The Agreement", "different agreement")
    assert token_f1("", "governing law") == (0.0, 0.0, 0.0)


def _gold_map():
    return {
        ("C1", "governing_law"): {
            "golds": [(0, 24, "laws of the state of Delaware")],
            "is_answerable": True,
        },
        ("C1", "non_compete"): {"golds": [], "is_answerable": False},
    }


def _pred(span_conf, cls_conf, text, key=("C1", "governing_law")):
    return {
        "contract_id": key[0], "clause_label": key[1],
        "span_confidence": span_conf, "cls_confidence": cls_conf,
        "start_char": 0, "end_char": len(text), "text": text,
    }


def test_score_answerable_and_no_answer_pairs():
    preds = [_pred(0.8, 0.1, "laws of the state of Delaware"),  # correct answerable
             _pred(0.3, 0.25, "whatever", ("C1", "non_compete"))]  # no-answer, margin .05 < delta .1
    res = score_prediction_set(preds, _gold_map(), no_answer_delta=0.1, min_confidence=0.05)
    ov = res["overall"]
    assert ov["answerable_em"] == 1.0 and ov["answerable_f1"] == 1.0
    assert ov["no_answer_accuracy"] == 1.0
    assert ov["found_decision"]["true_positive"] == 1
    assert ov["found_decision"]["false_positive"] == 0


def test_multi_gold_best_match_wins():
    gold = {("C1", "governing_law"): {"golds": [
        (0, 10, "completely different words here"),
        (0, 24, "laws of the state of Delaware"),
    ], "is_answerable": True}}
    preds = [_pred(0.8, 0.1, "laws of the state of Delaware")]
    res = score_prediction_set(preds, gold, 0.1, 0.05)
    assert res["overall"]["answerable_f1"] == 1.0


def test_missed_answerable_pair_counts_as_zero():
    preds = [_pred(0.1, 0.9, "")]
    res = score_prediction_set(preds, _gold_map(), 0.1, 0.05)
    ov = res["overall"]
    assert ov["answerable_em"] == 0.0
    assert ov["found_decision"]["false_negative"] == 1


def test_false_positive_on_no_answer_pair():
    preds = [_pred(0.9, 0.1, "hallucinated text"), ("C1", "governing_law") and
             _pred(0.2, 0.15, "span text", ("C1", "non_compete"))]
    res = score_prediction_set(preds, _gold_map(), 0.02, 0.05)
    ov = res["overall"]
    assert ov["found_decision"]["false_positive"] == 1
    assert ov["no_answer_accuracy"] == 0.0


def test_sweep_thresholds_sorted_by_macro_f1():
    preds = [_pred(0.8, 0.1, "laws of the state of Delaware"),
             _pred(0.2, 0.19, "x", ("C1", "non_compete"))]
    out = sweep_thresholds(preds, _gold_map(),
                           deltas=[0.0, 0.05, 0.1], min_confs=[0.0, 0.05])
    assert out[0]["macro_f1"] >= out[-1]["macro_f1"]


def test_training_sampling_and_collate():
    from ml.src.train import collate, sample_train_rows

    rows = ([{"input_ids": [1, 2, 3], "start_position": 1, "end_position": 2,
              "is_no_answer": False, "contract_id": "C", "clause_label": "l",
              "qa_id": "q", "window_index": 0, "gold_char_start": 0, "gold_char_end": 2}]
            + [{"input_ids": [4, 5, 6, 7], "start_position": 0, "end_position": 0,
                "is_no_answer": True, "contract_id": f"C{i}", "clause_label": "l",
                "qa_id": "q", "window_index": i, "gold_char_start": None,
                "gold_char_end": None} for i in range(20)])
    sampled, stats = sample_train_rows(rows, negative_ratio=3.0, seed=42)
    assert stats["positives_kept"] == 1
    assert stats["negatives_kept"] == 3
    again, _ = sample_train_rows(rows, negative_ratio=3.0, seed=42)
    assert [r["contract_id"] for r in sampled] == [r["contract_id"] for r in again]

    batch = collate(sampled, pad_id=0)
    assert batch["input_ids"].shape == (4, 4)  # padded to longest row
    pos_idx = next(i for i, r in enumerate(sampled) if r["contract_id"] == "C")
    assert (batch["input_ids"][pos_idx] == 0).sum().item() == 1  # 3-token positive row padded
    assert batch["attention_mask"][pos_idx].sum().item() == 3
