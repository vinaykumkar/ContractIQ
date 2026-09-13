#!/usr/bin/env python
"""Phase 3 threshold calibration + validation metrics (validation ONLY).

1. Runs the ContractAnalyzer (zero-shot baseline) over the validation split
   with the frozen retrieval strategy, saving RAW predictions (no threshold).
2. Sweeps (no_answer_delta, min_confidence) and selects the threshold pair
   maximizing macro F1 of the found-decision, tie-broken by answerable EM.
3. Writes the chosen thresholds into ml/configs/model.json and produces
   reports/phase3_calibration.json.

The official test set is NEVER touched here.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.src.config import ML_CONFIG_DIR, REPORTS_DIR, load_enabled_clauses  # noqa: E402
from ml.src.cuad_loader import load_train_contracts  # noqa: E402
from ml.src.evaluate import sweep_thresholds  # noqa: E402
from ml.src.preprocessing import VAL, assign_splits  # noqa: E402

DELTAS = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]
MIN_CONFS = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contracts", type=int, default=0,
                    help="limit val contracts (0 = all 41)")
    args = ap.parse_args()

    from ml.src.inference import ContractAnalyzer

    clauses = load_enabled_clauses()
    records = load_train_contracts(clauses, strict=True)
    assign_splits(records, seed=42, val_fraction=0.10)
    val = [r for r in records if r.split == VAL]
    if args.contracts:
        val = val[: args.contracts]
    print(f"Calibrating on {len(val)} validation contracts "
          f"(model state: to be resolved by analyzer)")

    analyzer = ContractAnalyzer(quiet=False)
    print(f"Model state: {analyzer.model_info['state']} "
          f"({analyzer.model_info['source']})")

    gold_by_pair = {}
    for rec in val:
        for clause in clauses:
            qas = rec.qas_for(clause.label)
            golds = [(qa.answers[0].start, qa.answers[0].end, qa.answers[0].text)
                     for qa in qas if not qa.is_impossible and qa.answers]
            gold_by_pair[(rec.contract_id, clause.label)] = {
                "golds": golds,
                "is_answerable": bool(golds),
            }

    predictions = []
    t0 = time.perf_counter()
    for i, rec in enumerate(val, 1):
        for label, raw, meta in analyzer.iter_raw(rec.context):
            predictions.append({
                "contract_id": rec.contract_id,
                "clause_label": label,
                "span_confidence": raw.span_confidence,
                "cls_confidence": raw.cls_confidence,
                "start_char": raw.start_char,
                "end_char": raw.end_char,
                "text": rec.context[raw.start_char:raw.end_char] if raw.start_char >= 0 else "",
                "windows": meta["windows"],
                "processing_ms": meta["processing_ms"],
            })
        el = time.perf_counter() - t0
        print(f"  [{i}/{len(val)}] {rec.contract_id[:44]} | {el:.0f}s elapsed "
              f"| ~{el/i:.0f}s per contract", flush=True)

    sweep = sweep_thresholds(predictions, gold_by_pair, DELTAS, MIN_CONFS)
    best = sweep[0]
    print(f"\nBest thresholds: delta={best['no_answer_delta']} "
          f"min_conf={best['min_confidence']} -> macro_f1={best['macro_f1']} "
          f"answerable_em={best['answerable_em']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "phase3_val_predictions_baseline.json").write_text(
        json.dumps(predictions), encoding="utf-8")
    (REPORTS_DIR / "phase3_calibration.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_state": analyzer.model_info["state"],
        "model_source": analyzer.model_info["source"],
        "val_contracts": len(val),
        "prediction_count": len(predictions),
        "total_seconds": round(time.perf_counter() - t0, 1),
        "grid": {"deltas": DELTAS, "min_confs": MIN_CONFS},
        "top_candidates": sweep[:10],
        "selected": best,
        "note": "Thresholds chosen on validation only; official test set untouched.",
    }, indent=2), encoding="utf-8")

    # persist chosen thresholds into model.json
    cfg_path = ML_CONFIG_DIR / "model.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["decoding"]["no_answer_delta"] = best["no_answer_delta"]
    cfg["decoding"]["min_confidence"] = best["min_confidence"]
    cfg["decoding"]["note"] = ("Calibrated on the validation split "
                               f"({len(val)} contracts, {analyzer.model_info['state']}); "
                               "never tuned on the official test set.")
    cfg["model_version"] = "phase3-baseline-minilm-squad2-calibrated"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"Updated {cfg_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
