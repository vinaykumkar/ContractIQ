#!/usr/bin/env python
"""Phase 3 OFFICIAL TEST evaluation — runs ONCE, after settings are frozen.

Requires:
- ml/configs/model.json with calibrated decoding thresholds
- frozen retrieval strategy and model choice

Safety: refuses to run if the output report already exists (use --force only
deliberately). Never used for tuning; results are final, whatever they are.

Writes reports/phase3_test_evaluation.{json,md} and
reports/phase3_test_predictions.json.
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

from ml.src.config import REPORTS_DIR, load_enabled_clauses  # noqa: E402
from ml.src.cuad_loader import load_test_contracts  # noqa: E402
from ml.src.evaluate import score_prediction_set  # noqa: E402

REPORT_JSON = REPORTS_DIR / "phase3_test_evaluation.json"
REPORT_MD = REPORTS_DIR / "phase3_test_evaluation.md"
PREDICTIONS = REPORTS_DIR / "phase3_test_predictions.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="re-run even though the report exists (new freeze required)")
    args = ap.parse_args()

    if REPORT_JSON.exists() and not args.force:
        print("REFUSING: reports/phase3_test_evaluation.json already exists.")
        print("The official test set is evaluated ONCE per frozen configuration. "
              "Use --force only after deliberately re-freezing settings.")
        return 1

    from ml.src.inference import ContractAnalyzer

    clauses = load_enabled_clauses()
    cfg = json.loads((PROJECT_ROOT / "ml/configs/model.json").read_text(encoding="utf-8"))

    # The freeze guard: thresholds in model.json must match a recorded
    # calibration run (any values, including legitimate 0.0/0.0).
    calibration_path = REPORTS_DIR / "phase3_calibration.json"
    if not calibration_path.exists():
        print("REFUSING: no calibration record found (reports/phase3_calibration.json). "
              "Run scripts/calibrate_thresholds.py first.")
        return 1
    cal = json.loads(calibration_path.read_text(encoding="utf-8"))
    sel = cal.get("selected", {})
    cfg_delta = float(cfg["decoding"]["no_answer_delta"])
    cfg_min_conf = float(cfg["decoding"]["min_confidence"])
    if (sel.get("no_answer_delta"), sel.get("min_confidence")) != (cfg_delta, cfg_min_conf):
        print(f"REFUSING: model.json thresholds ({cfg_delta}, {cfg_min_conf}) do not match "
              f"the recorded calibration ({sel.get('no_answer_delta')}, {sel.get('min_confidence')}). "
              "Re-freeze settings before evaluating on the official test set.")
        return 1

    print("Loading official test set (102 contracts, strict validation)...")
    records = load_test_contracts(clauses, strict=True)
    print(f"  {len(records)} contracts")

    analyzer = ContractAnalyzer(quiet=False)
    print(f"Model state: {analyzer.model_info['state']} ({analyzer.model_info['source']})")
    print(f"Frozen decoding: {cfg['decoding']}")

    gold_by_pair = {}
    for rec in records:
        for clause in clauses:
            qas = rec.qas_for(clause.label)
            golds = [(qa.answers[0].start, qa.answers[0].end, qa.answers[0].text)
                     for qa in qas if not qa.is_impossible and qa.answers]
            gold_by_pair[(rec.contract_id, clause.label)] = {
                "golds": golds, "is_answerable": bool(golds),
            }

    predictions = []
    t0 = time.perf_counter()
    for i, rec in enumerate(records, 1):
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
        print(f"  [{i}/{len(records)}] {rec.contract_id[:44]} | {el:.0f}s "
              f"| ~{el/i:.0f}s per contract", flush=True)

    results = score_prediction_set(
        predictions, gold_by_pair,
        no_answer_delta=float(cfg["decoding"]["no_answer_delta"]),
        min_confidence=float(cfg["decoding"]["min_confidence"]),
    )
    rows = results.pop("rows")
    total_windows = sum(p["windows"] for p in predictions)
    total_ms = sum(p["processing_ms"] for p in predictions)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_note": "Official test evaluation, run ONCE after settings were frozen "
                    "(model, thresholds, retrieval, quantization).",
        "model_state": analyzer.model_info["state"],
        "model_source": analyzer.model_info["source"],
        "model_version": analyzer.model_info["model_version"],
        "frozen_decoding": cfg["decoding"],
        "frozen_retrieval": {k: v for k, v in cfg["retrieval"].items() if k != "note"},
        "test_contracts": len(records),
        "prediction_count": len(predictions),
        "total_windows_processed": total_windows,
        "total_processing_seconds": round(total_ms / 1000, 1),
        "avg_windows_per_contract": round(total_windows / len(records), 1),
        "results": results,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    PREDICTIONS.write_text(json.dumps(predictions), encoding="utf-8")

    ov = report["results"]["overall"]
    fd = ov["found_decision"]
    md = ["# ContractIQ — Phase 3 Official Test Evaluation", "",
          f"_Generated: {report['generated_at']}_ · Run ONCE on the untouched 102-contract test set.", "",
          f"Model: **{report['model_state']}** (`{report['model_source']}`) · version `{report['model_version']}`",
          f"Frozen decoding: delta={cfg['decoding']['no_answer_delta']}, "
          f"min_confidence={cfg['decoding']['min_confidence']}", "",
          "## Overall", "",
          "| Metric | Value |", "|---|---:|",
          f"| Overall EM (SQuAD2 convention) | {ov['em']*100:.1f}% |",
          f"| Overall F1 | {ov['f1']*100:.1f}% |",
          f"| Answerable EM ({ov['answerable_pairs']} pairs) | {ov['answerable_em']*100:.1f}% |",
          f"| Answerable F1 | {ov['answerable_f1']*100:.1f}% |",
          f"| Answerable precision / recall | {ov['answerable_precision']*100:.1f}% / {ov['answerable_recall']*100:.1f}% |",
          f"| No-answer accuracy ({ov['no_answer_pairs']} pairs) | {ov['no_answer_accuracy']*100:.1f}% |",
          f"| Answerable-detection recall / found-precision / macro F1 | "
          f"{fd['answerable_detection_recall']*100:.1f}% / {fd['found_precision']*100:.1f}% / {fd['macro_f1']*100:.1f}% |",
          "", "## Per-clause", "",
          "| Clause | Pairs | Answerable | EM | F1 | Answerable F1 | No-answer acc. |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for label, m in sorted(report["results"]["per_clause"].items()):
        a_f1 = "n/a" if m["answerable_f1"] is None else f"{m['answerable_f1']*100:.1f}%"
        na = "n/a" if m["no_answer_accuracy"] is None else f"{m['no_answer_accuracy']*100:.1f}%"
        md.append(f"| {label} | {m['pairs']} | {m['answerable_pairs']} | {m['em']*100:.1f}% | "
                  f"{m['f1']*100:.1f}% | {a_f1} | {na} |")
    md += ["", f"Runtime: {report['total_processing_seconds']:.0f}s model time · "
               f"avg {report['avg_windows_per_contract']} windows/contract (with frozen retrieval).", ""]
    REPORT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {REPORT_JSON} and {REPORT_MD}")
    ov = report["results"]["overall"]
    print(f"Overall EM {ov['em']*100:.1f}% | F1 {ov['f1']*100:.1f}% | "
          f"answerable F1 {ov['answerable_f1']*100:.1f}% | "
          f"no-answer acc {ov['no_answer_accuracy']*100:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
