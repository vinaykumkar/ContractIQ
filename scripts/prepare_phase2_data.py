#!/usr/bin/env python
"""Phase 2 full feature preparation for the 15 Version-1 clauses.

- Loads all 408 official training contracts (strict answer validation).
- Deterministic contract-level 90/10 train/val split (seed=42).
- Official test set is untouched (leakage report proves zero overlap).
- Streams train features (token labels, CLS no-answer) and val eval features
  (char offsets) to Parquet shards under data/processed/ with bounded RAM.
- Writes reports/phase2_preprocessing.{json,md}.

Usage:  python scripts/prepare_phase2_data.py [--force]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.src.chunking import build_windows_for_clause, tokenize_context  # noqa: E402
from ml.src.config import (  # noqa: E402
    PROCESSED_DIR,
    REPORTS_DIR,
    TEST_PATH,
    load_enabled_clauses,
    load_window_config,
)
from ml.src.cuad_loader import load_train_contracts  # noqa: E402
from ml.src.qa_features import answer_token_positions, cls_index  # noqa: E402
from ml.src.preprocessing import (  # noqa: E402
    TRAIN,
    VAL,
    FeatureWriter,
    EVAL_SCHEMA,
    TRAIN_SCHEMA,
    assign_splits,
    leakage_report,
    question_budget,
    save_split_metadata,
)

SHARD_ROWS = 10_000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rebuild even if outputs exist")
    args = ap.parse_args()

    from transformers import AutoTokenizer

    clauses = load_enabled_clauses()
    config = load_window_config()
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased", use_fast=True)
    config.check_tokenizer_compat(tokenizer.model_max_length)
    cls_id, sep_id = tokenizer.cls_token_id, tokenizer.sep_token_id

    train_out = PROCESSED_DIR / "train_features"
    val_out = PROCESSED_DIR / "val_eval_features"
    if not args.force and train_out.exists() and val_out.exists():
        print("Outputs already exist (use --force to rebuild). Skipping.")
        return 0

    t0 = time.perf_counter()
    print("Loading 408 training contracts (strict answer validation)...")
    records = load_train_contracts(clauses, strict=True)
    print(f"  loaded {len(records)} contracts in {time.perf_counter() - t0:.1f}s")

    # ---- split ----
    info = assign_splits(records, seed=42, val_fraction=0.10)
    save_split_metadata(info, PROCESSED_DIR / "split_metadata.json")
    print(f"Split: {info.counts} (seed={info.seed})")

    with TEST_PATH.open("r", encoding="utf-8") as f:
        test_titles = [item["title"] for item in json.load(f)["data"]]
    leak = leakage_report(info.train_ids, info.val_ids, test_titles)
    assert not leak["train_overlap_val"] and not leak["train_overlap_test"] \
        and not leak["val_overlap_test"], "LEAKAGE DETECTED"
    print("Leakage check: clean")

    # ---- stream features ----
    writer_train = FeatureWriter(train_out, TRAIN_SCHEMA, shard_rows=SHARD_ROWS)
    writer_val = FeatureWriter(val_out, EVAL_SCHEMA, shard_rows=SHARD_ROWS)

    per_clause_windows = {c.label: 0 for c in clauses}
    per_clause_positive = {c.label: 0 for c in clauses}
    windows_per_contract_clause: list[int] = []
    mid_token_spans: set[tuple] = set()
    all_gold_spans: set[tuple] = set()

    t1 = time.perf_counter()
    n = len(records)
    for i, rec in enumerate(records, 1):
        tokenized = tokenize_context(tokenizer, rec)
        for clause in clauses:
            q_ids = tokenizer(clause.question, add_special_tokens=False)["input_ids"]
            windows = build_windows_for_clause(
                tokenized, q_ids, clause.label, config, cls_id, sep_id
            )
            per_clause_windows[clause.label] += len(windows)
            windows_per_contract_clause.append(len(windows))
            if rec.split == TRAIN:
                golds = [qa for qa in rec.qas
                         if qa.clause_label == clause.label
                         and not qa.is_impossible and qa.answers]
                for w in windows:
                    label_pos, label_chars, source_qa = None, None, ""
                    for qa in golds:
                        pos = answer_token_positions(w, qa.answers[0])
                        if pos is not None:
                            label_pos, label_chars, source_qa = pos, (qa.answers[0].start, qa.answers[0].end), qa.qa_id
                            break
                    if label_pos is None:
                        source_qa = next((qa.qa_id for qa in rec.qas
                                          if qa.clause_label == clause.label), "")
                        writer_train.add({
                            "input_ids": w.input_ids,
                            "start_position": cls_index(),
                            "end_position": cls_index(),
                            "contract_id": w.contract_id,
                            "clause_label": w.clause_label,
                            "qa_id": source_qa,
                            "window_index": w.window_index,
                            "is_no_answer": True,
                            "gold_char_start": None,
                            "gold_char_end": None,
                        })
                    else:
                        per_clause_positive[clause.label] += 1
                        local_s = label_pos[0] - w.ctx_first_token_index_in_window
                        local_e = label_pos[1] - w.ctx_first_token_index_in_window
                        char_s = w.ctx_offsets[local_s][0]
                        char_e = w.ctx_offsets[local_e][1]
                        span_key = (rec.contract_id, clause.label, label_chars[0], label_chars[1])
                        all_gold_spans.add(span_key)
                        if char_s != label_chars[0] or char_e != label_chars[1]:
                            mid_token_spans.add(span_key)
                        writer_train.add({
                            "input_ids": w.input_ids,
                            "start_position": label_pos[0],
                            "end_position": label_pos[1],
                            "contract_id": w.contract_id,
                            "clause_label": w.clause_label,
                            "qa_id": source_qa,
                            "window_index": w.window_index,
                            "is_no_answer": False,
                            "gold_char_start": label_chars[0],
                            "gold_char_end": label_chars[1],
                        })
            else:
                qa_id = next((qa.qa_id for qa in rec.qas
                              if qa.clause_label == clause.label), "")
                is_na = not golds_or_false(rec, clause.label)
                for w in windows:
                    writer_val.add({
                        "input_ids": w.input_ids,
                        "contract_id": w.contract_id,
                        "clause_label": w.clause_label,
                        "qa_id": qa_id,
                        "window_index": w.window_index,
                        "is_no_answer_example": is_na,
                        "offset_start": [o[0] for o in w.ctx_offsets],
                        "offset_end": [o[1] for o in w.ctx_offsets],
                    })
        if i % 50 == 0 or i == n:
            ram = _ram_gb()
            print(f"  [{i:>3}/{n}] contracts | train rows {writer_train.rows_written:,} | "
                  f"val rows {writer_val.rows_written:,} | RAM {ram:.2f} GB | {time.perf_counter() - t1:.0f}s")

    train_files, train_rows = writer_train.close()
    val_files, val_rows = writer_val.close()
    elapsed = time.perf_counter() - t0

    no_answer_train = train_rows - sum(per_clause_positive.values())
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tokenizer": "distilbert-base-uncased",
        "tokenizer_model_max_length": tokenizer.model_max_length,
        "window_config": {
            "max_seq_len": config.max_seq_len,
            "doc_stride": config.doc_stride,
            "max_answer_tokens": config.max_answer_tokens,
        },
        "split": {
            "seed": info.seed,
            "val_fraction": info.val_fraction,
            "level": "contract",
            "train_contracts": len(info.train_ids),
            "val_contracts": len(info.val_ids),
            "official_test_contracts": len(test_titles),
            "leakage_report": leak,
        },
        "features": {
            "train_rows": train_rows,
            "val_eval_rows": val_rows,
            "train_positive_windows": sum(per_clause_positive.values()),
            "train_no_answer_windows": no_answer_train,
            "positive_share": round(sum(per_clause_positive.values()) / train_rows, 4) if train_rows else 0,
            "windows_per_contract_clause": {
                "max": max(windows_per_contract_clause),
                "median": int(median(windows_per_contract_clause)),
                "mean": round(sum(windows_per_contract_clause) / len(windows_per_contract_clause), 1),
            },
            "per_clause": {
                c.label: {
                    "cuad_category": c.cuad_category,
                    "windows": per_clause_windows[c.label],
                    "positive_windows": per_clause_positive[c.label],
                }
                for c in clauses
            },
        },
        "data_anomalies": {
            "gold_spans_cut_mid_token": len(mid_token_spans),
            "unique_gold_spans_seen_in_train_windows": len(all_gold_spans),
            "mid_token_share": round(len(mid_token_spans) / len(all_gold_spans), 4) if all_gold_spans else 0,
            "note": "Gold spans whose boundary falls inside a wordpiece token; "
                    "training labels use the containing token (standard SQuAD).",
        },
        "question_budget": question_budget(clauses, config, tokenizer),
        "performance": {
            "total_wall_seconds": round(elapsed, 1),
            "peak_ram_gb": _ram_gb(),
            "shard_rows": SHARD_ROWS,
            "train_shard_files": len(train_files),
            "val_shard_files": len(val_files),
        },
        "outputs": {
            "train_features_dir": str(train_out.relative_to(PROJECT_ROOT)),
            "val_eval_features_dir": str(val_out.relative_to(PROJECT_ROOT)),
            "split_metadata": str((PROCESSED_DIR / "split_metadata.json").relative_to(PROJECT_ROOT)),
        },
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "phase2_preprocessing.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    (REPORTS_DIR / "phase2_preprocessing.md").write_text(build_md(report), encoding="utf-8")

    print(f"\nDone in {elapsed:.0f}s. Train rows: {train_rows:,} | Val rows: {val_rows:,}")
    print(f"Positive windows: {sum(per_clause_positive.values()):,} | "
          f"No-answer windows: {no_answer_train:,}")
    print(f"Peak RAM: {_ram_gb():.2f} GB")
    return 0


def golds_or_false(rec, label) -> bool:
    return any(qa.clause_label == label and not qa.is_impossible and qa.answers
               for qa in rec.qas)


def _ram_gb() -> float:
    import psutil

    return psutil.Process().memory_info().rss / 1e9


def build_md(r: dict) -> str:
    lines = []
    a = lines.append
    a("# ContractIQ — Phase 2 Preprocessing Report")
    a("")
    a(f"_Generated: {r['generated_at']}_")
    a("")
    a("## Split & leakage")
    a("")
    sp = r["split"]
    lr = sp["leakage_report"]
    a(f"- Deterministic contract-level split: **{sp['train_contracts']} train / "
      f"{sp['val_contracts']} val** (seed={sp['seed']}, val_fraction={sp['val_fraction']}) "
      f"carved only from the 408 official training contracts.")
    a(f"- Official test set: **{sp['official_test_contracts']} contracts, untouched**.")
    a(f"- Overlaps train∩val={len(lr['train_overlap_val'])}, train∩test={len(lr['train_overlap_test'])}, "
      f"val∩test={len(lr['val_overlap_test'])} — all must be 0.")
    a("")
    a("## Features")
    a("")
    f = r["features"]
    a(f"- Train windows: **{f['train_rows']:,}** (positive {f['train_positive_windows']:,} / "
      f"no-answer {f['train_no_answer_windows']:,} → {f['positive_share']*100:.1f}% positive)")
    a(f"- Validation eval windows: **{f['val_eval_rows']:,}**")
    w = f["windows_per_contract_clause"]
    a(f"- Windows per (contract, clause): median {w['median']}, max {w['max']}")
    a("")
    a("| Clause | CUAD category | Windows | Positive windows |")
    a("|---|---|---:|---:|")
    for label, v in f["per_clause"].items():
        a(f"| `{label}` | {v['cuad_category']} | {v['windows']:,} | {v['positive_windows']:,} |")
    a("")
    a("## Question token budget")
    a("")
    a("| Clause | Question tokens | Context budget (of 512) | At risk |")
    a("|---|---:|---:|---|")
    for q in r["question_budget"]:
        a(f"| `{q['label']}` | {q['question_tokens']} | {q['context_budget']} | {q['at_risk']} |")
    a("")
    a("## Data anomalies")
    a("")
    d = r["data_anomalies"]
    a(f"- Gold spans cut mid-wordpiece-token: **{d['gold_spans_cut_mid_token']}** of "
      f"{d['unique_gold_spans_seen_in_train_windows']} unique spans "
      f"({d['mid_token_share']*100:.1f}%). Labels use the containing token (standard); "
      "exact char offsets stay in feature metadata.")
    a("")
    a("## Performance")
    a("")
    p = r["performance"]
    a(f"- Preparation wall time: {p['total_wall_seconds']:.0f}s · peak RSS {p['peak_ram_gb']:.2f} GB · "
      f"{p['train_shard_files']}+{p['val_shard_files']} Parquet shards ({p['shard_rows']:,} rows each)")
    a("")
    a("## Storage")
    a("")
    a(f"- `{r['outputs']['train_features_dir']}` — train features (input_ids, start/end, metadata)")
    a(f"- `{r['outputs']['val_eval_features_dir']}` — eval features (input_ids, char offsets, metadata)")
    a(f"- `{r['outputs']['split_metadata']}` — reproducible split (ids + seed)")
    a("")
    a("Contract text is NOT duplicated per window; features store token ids and offsets, "
      "and everything is reproducible from data/raw/ via this script.")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
