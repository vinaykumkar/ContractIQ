#!/usr/bin/env python
"""Phase 2 pretrained QA smoke test (NOT an accuracy evaluation).

Proves the end-to-end chain: tokenizer -> model -> window batching -> logits
-> answer decoding -> original-char offsets -> confidence, using a free
lightweight extractive-QA model:

    distilbert/distilbert-base-uncased-distilled-squad
    - intended task: question-answering (extractive)
    - size: 66.4M params (~253 MB fp32)
    - license: Apache-2.0
    - runs on CPU

No fine-tuning, no metrics, no test-set usage. Zero-shot behaviour on legal
text is expected to be weak - this only proves plumbing.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.src.chunking import build_windows_for_clause, tokenize_context  # noqa: E402
from ml.src.config import (  # noqa: E402
    PROCESSED_DIR,
    REPORTS_DIR,
    load_enabled_clauses,
    load_window_config,
)
from ml.src.cuad_loader import load_train_contracts  # noqa: E402
from ml.src.preprocessing import VAL, assign_splits  # noqa: E402

MODEL_ID = "distilbert/distilbert-base-uncased-distilled-squad"
CLAUSES_TO_TRY = ["governing_law", "renewal_term", "non_compete"]
MAX_EXAMPLES = 6  # (contract, clause) pairs - deliberately tiny


def best_span_in_window(start_logits, end_logits, ctx_start, ctx_end, max_answer_tokens):
    """Best (start, end) inside the context slice + confidence p_start*p_end."""
    s = torch.softmax(start_logits[ctx_start:ctx_end], dim=-1)
    e = torch.softmax(end_logits[ctx_start:ctx_end], dim=-1)
    best = (0, 0, -1.0)
    n = len(s)
    for i in range(n):
        for j in range(i, min(i + max_answer_tokens, n)):
            score = float(s[i] * e[j])
            if score > best[2]:
                best = (i, j, score)
    return best


def main() -> int:
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer

    clauses = {c.label: c for c in load_enabled_clauses()}
    config = load_window_config()
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased", use_fast=True)
    config.check_tokenizer_compat(tokenizer.model_max_length)

    t0 = time.perf_counter()
    model = AutoModelForQuestionAnswering.from_pretrained(MODEL_ID)
    model.eval()
    print(f"Model loaded in {time.perf_counter() - t0:.1f}s")

    # two deterministic validation contracts (never the official test set)
    records = load_train_contracts(load_enabled_clauses(), strict=True)
    info = assign_splits(records, seed=42, val_fraction=0.10)
    val_records = [r for r in records if r.split == VAL][:2]
    assert val_records, "no val contracts selected"

    results = []
    n_done = 0
    with torch.inference_mode():
        for rec in val_records:
            tokenized = tokenize_context(tokenizer, rec)
            for label in CLAUSES_TO_TRY:
                if n_done >= MAX_EXAMPLES:
                    break
                clause = clauses[label]
                q_ids = tokenizer(clause.question, add_special_tokens=False)["input_ids"]
                windows = build_windows_for_clause(
                    tokenized, q_ids, label, config,
                    tokenizer.cls_token_id, tokenizer.sep_token_id,
                )
                if not windows:
                    continue
                t1 = time.perf_counter()
                # batched forward over ALL windows of this (contract, clause);
                # pad variable-length windows to the batch max with attention 0
                pad_id = tokenizer.pad_token_id
                max_len = max(len(w.input_ids) for w in windows)
                batch = torch.tensor(
                    [w.input_ids + [pad_id] * (max_len - len(w.input_ids)) for w in windows],
                    dtype=torch.long,
                )
                attention = torch.tensor(
                    [[1] * len(w.input_ids) + [0] * (max_len - len(w.input_ids)) for w in windows],
                    dtype=torch.long,
                )
                outputs = model(input_ids=batch, attention_mask=attention)
                elapsed = time.perf_counter() - t1

                # pick the best span across windows (context tokens only)
                best = None
                for wi, w in enumerate(windows):
                    ctx_from = w.ctx_first_token_index_in_window
                    ctx_to = ctx_from + (w.ctx_token_end - w.ctx_token_start)
                    i, j, score = best_span_in_window(
                        outputs.start_logits[wi], outputs.end_logits[wi],
                        ctx_from, ctx_to, config.max_answer_tokens,
                    )
                    if best is None or score > best[2]:
                        best = (wi, i, j, score)
                wi, i, j, score = best
                w = windows[wi]
                local_s = i - w.ctx_first_token_index_in_window
                local_e = j - w.ctx_first_token_index_in_window
                char_s = w.ctx_offsets[local_s][0]
                char_e = w.ctx_offsets[local_e][1]
                text = rec.context[char_s:char_e]

                results.append({
                    "contract_id": rec.contract_id,
                    "clause": label,
                    "windows": len(windows),
                    "forward_seconds": round(elapsed, 3),
                    "confidence": round(score, 4),
                    "char_offsets": [char_s, char_e],
                    "extracted_text": text[:300],
                })
                print(f"\n[{rec.contract_id[:40]}... | {label}] "
                      f"{len(windows)} windows in {elapsed:.2f}s "
                      f"({len(windows)/elapsed:.1f} win/s)")
                print(f"  confidence={score:.3f} -> {text[:160]!r}")
                n_done += 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "id": MODEL_ID,
            "task": "question-answering (extractive)",
            "license": "apache-2.0",
            "parameters": "~66.4M (fp32, ~253 MB)",
        },
        "device": "cpu",
        "torch_version": torch.__version__,
        "note": "SMOKE TEST ONLY - proves the inference plumbing end to end. "
                "Confidence numbers are zero-shot proxy scores, NOT model performance.",
        "examples": results,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / "phase2_smoke_test.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSmoke test complete: {n_done} examples. Report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
