"""Extractive QA evaluation with SQuAD-style normalization and no-answer logic.

Metric conventions (documented):
- Predictions are normalized like SQuAD: lowercase, remove punctuation,
  remove articles (a/an/the), collapse whitespace.
- Multi-gold: a prediction is scored against ALL gold spans of the
  (contract, clause) pair; the BEST match counts.
- Answerable pairs: EM = 1 iff normalized prediction equals some gold;
  F1/precision/recall = token-overlap against the best-matching gold.
- No-answer pairs: the model is correct iff it reports found=False; EM/F1 = 1
  when correct, 0 otherwise (SQuAD2 convention).
- "found decision" metrics treat answerable pairs as the positive class
  (recall) and no-answer pairs as the negative class (precision), combined
  into the macro F1 used for threshold calibration on validation only.
"""
from __future__ import annotations

import re
import string
from collections import defaultdict


def normalize_answer(text: str) -> str:
    text = text.lower()
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def token_f1(pred_text: str, gold_text: str) -> tuple[float, float, float]:
    """(f1, precision, recall) of token overlap between normalized texts.

    Uses bag-of-words (Counter) intersection exactly like the official SQuAD
    metric - repeated tokens count, so identical strings score 1.0.
    """
    from collections import Counter

    pred = normalize_answer(pred_text).split()
    gold = normalize_answer(gold_text).split()
    if not pred or not gold:
        return 0.0, 0.0, 0.0
    common = Counter(pred) & Counter(gold)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0, 0.0, 0.0
    precision = num_same / len(pred)
    recall = num_same / len(gold)
    f1 = 2 * precision * recall / (precision + recall)
    return f1, precision, recall


def exact_match(pred_text: str, gold_text: str) -> bool:
    return normalize_answer(pred_text) == normalize_answer(gold_text)


def score_prediction_set(
    predictions: list[dict],
    gold_by_pair: dict[tuple[str, str], dict],
    no_answer_delta: float,
    min_confidence: float,
) -> dict:
    """Score a saved prediction set against gold under given thresholds.

    predictions: [{contract_id, clause_label, span_confidence, cls_confidence,
                   start_char, end_char, text}, ...]
    gold_by_pair: {(contract_id, clause_label):
                   {"golds": [(start, end, text), ...], "is_answerable": bool}}
    """
    per_pair = []
    for p in predictions:
        key = (p["contract_id"], p["clause_label"])
        gold = gold_by_pair.get(key)
        if gold is None:
            continue
        found = (
            p["span_confidence"] >= min_confidence
            and (p["span_confidence"] - p["cls_confidence"]) >= no_answer_delta
        )
        pred_text = p["text"] if found else ""
        row = {
            "contract_id": p["contract_id"],
            "clause_label": p["clause_label"],
            "is_answerable": gold["is_answerable"],
            "found_decision": bool(found),
        }
        if gold["is_answerable"]:
            best_em = 0.0
            best_f1 = best_p = best_r = 0.0
            for _, _, gtext in gold["golds"]:
                best_em = max(best_em, 1.0 if exact_match(pred_text, gtext) else 0.0)
                f1, pr, rc = token_f1(pred_text, gtext)
                best_f1, best_p, best_r = max(best_f1, f1), max(best_p, pr), max(best_r, rc)
            row.update({"em": best_em, "f1": best_f1, "precision": best_p, "recall": best_r})
        else:
            correct = not found
            row.update({
                "em": 1.0 if correct else 0.0,
                "f1": 1.0 if correct else 0.0,
                "no_answer_correct": correct,
            })
        per_pair.append(row)

    # aggregates
    ans = [r for r in per_pair if r["is_answerable"]]
    non = [r for r in per_pair if not r["is_answerable"]]
    def avg(rows, key):
        return sum(r[key] for r in rows) / len(rows) if rows else 0.0

    tp = sum(1 for r in ans if r["found_decision"])
    fn = len(ans) - tp
    fp = sum(1 for r in non if r["found_decision"])
    tn = len(non) - fp
    answerable_recall = tp / len(ans) if ans else 0.0
    found_precision = tp / (tp + fp) if (tp + fp) else 0.0
    decision_f1 = (2 * answerable_recall * found_precision / (answerable_recall + found_precision)
                   if (answerable_recall + found_precision) else 0.0)

    overall = {
        "em": avg(per_pair, "em"),
        "f1": avg(per_pair, "f1"),
        "answerable_em": avg(ans, "em"),
        "answerable_f1": avg(ans, "f1"),
        "answerable_precision": avg(ans, "precision"),
        "answerable_recall": avg(ans, "recall"),
        "answerable_pairs": len(ans),
        "no_answer_accuracy": avg(non, "no_answer_correct") if non else 0.0,
        "no_answer_pairs": len(non),
        "found_decision": {
            "true_positive": tp, "false_negative": fn, "false_positive": fp, "true_negative": tn,
            "answerable_detection_recall": round(answerable_recall, 4),
            "found_precision": round(found_precision, 4),
            "macro_f1": round(decision_f1, 4),
        },
    }

    per_clause = defaultdict(list)
    for r in per_pair:
        per_clause[r["clause_label"]].append(r)
    clause_metrics = {}
    for label, rows in per_clause.items():
        a = [r for r in rows if r["is_answerable"]]
        n = [r for r in rows if not r["is_answerable"]]
        clause_metrics[label] = {
            "pairs": len(rows),
            "answerable_pairs": len(a),
            "em": avg(rows, "em"),
            "f1": avg(rows, "f1"),
            "answerable_f1": avg(a, "f1") if a else None,
            "no_answer_accuracy": (sum(1 for r in n if r["no_answer_correct"]) / len(n)) if n else None,
        }
    return {"overall": overall, "per_clause": clause_metrics, "rows": per_pair}


def sweep_thresholds(
    predictions: list[dict],
    gold_by_pair: dict[tuple[str, str], dict],
    deltas: list[float],
    min_confs: list[float],
) -> list[dict]:
    """Evaluate a threshold grid; returns candidates sorted by macro F1."""
    out = []
    for d in deltas:
        for mc in min_confs:
            res = score_prediction_set(predictions, gold_by_pair, d, mc)
            ov = res["overall"]
            out.append({
                "no_answer_delta": d,
                "min_confidence": mc,
                "macro_f1": ov["found_decision"]["macro_f1"],
                "answerable_em": ov["answerable_em"],
                "answerable_f1": ov["answerable_f1"],
                "overall_f1": ov["f1"],
                "overall_em": ov["em"],
            })
    out.sort(key=lambda x: (-x["macro_f1"], -x["answerable_em"], x["no_answer_delta"]))
    return out
