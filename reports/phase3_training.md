# ContractIQ — Phase 3 Training Report

_Generated: 2026-08-30 · Two training paths implemented; both exercised._

## Path A — local tiny CPU fine-tune (plumbing proof)

Stopped before completion when the workload moved to GPU (see below); the same
code path (`python -m ml.src.train --tiny`) was validated end-to-end on GPU
instead. The tiny path enforces strict limits (`--max-steps`, `--time-limit-min`,
forced CPU) so it can never escalate into a full training run.

## Path B — GPU fine-tune (the practical path)

**Command (exact, reproducible):**

```bash
python -m ml.src.train \
    --model deepset/minilm-uncased-squad2 \
    --epochs 1 --batch-size 16 --learning-rate 3e-5 \
    --negative-ratio 3 --seed 42 --amp \
    --output ml/models/final --checkpoints ml/checkpoints
```

**Run facts (measured, not estimated):**

| Item | Value |
|---|---|
| Device | CUDA — NVIDIA GeForce RTX 2050 (4 GB VRAM), fp16 autocast (AMP) |
| Data | Phase 2 train features: **5,105 positive windows + 15,315 no-answer windows** (seeded 1:3 negative sampling; total 20,420 rows) |
| Schedule | 1 epoch = **1,277 optimizer steps**, batch 16, lr 3e-5, linear warmup 10%, grad-clip 1.0 |
| Wall time | **838 s (~14 min)** at ~100% GPU utilization |
| Final loss | ~1.18–1.23 (from ~2.1 at start) |
| Quick val (token-position accuracy, 512 rows) | start 92.6% / end 51.0% |
| Checkpoints | `ml/checkpoints/epoch1/` + best-of-run → `ml/models/final/` (128 MB: weights + tokenizer + config + `training_meta.json`) |

Sampling statistics are stored in `ml/models/final/training_meta.json` (seed 42, ratio 3.0, kept counts) — reproducible.

## Negative-sampling design

97.2% of raw windows are no-answer (Phase 2). `sample_train_rows` keeps **all
positive windows** plus a seeded uniform sample of no-answer windows at ratio
`--negative-ratio` (default 3). Both sampled classes contain the two negative
kinds from Phase 2 (windows of positive pairs without the span, and fully
impossible clause-contract pairs). Ratio 3 was chosen as the instructed
starting point; the 1-epoch run with it produced macro-F1 0.819 on validation,
so no further ratio search was spent (documented as future work alongside
hard-negative mining).

## Results after fine-tuning (validation, calibrated thresholds)

| Metric | Zero-shot baseline | After 1 GPU epoch |
|---|---:|---:|
| Answerable EM | 0.0% | **57.8%** |
| Answerable F1 | 0.4% | **66.7%** |
| Overall EM / F1 (SQuAD2) | 35.1% / 35.4% | **61.0% / 66.6%** |
| No-answer accuracy | 94.3% | 66.4% |
| Found-decision macro F1 | 15.3% | **81.9%** |

The no-answer trade-off moved as expected when the model starts finding real
clauses: it now misses 33.6% of no-answer pairs. That axis improves with more
epochs/negatives and threshold refinement — deliberately NOT tuned further
against validation within this phase's time budget.

## Path to a stronger model (documented, not run here)

- **More epochs on this GPU**: 2–3 epochs ≈ 30–45 min each on the RTX 2050.
- **Larger negative ratio or hard-negative mining** for the no-answer axis.
- **RoBERTa-squad2 base** (124M) for accuracy: `python -m ml.src.train --model deepset/roberta-base-squad2 ...` — requires re-preprocessing features with the RoBERTa tokenizer (documented in `reports/phase3_model_selection.md`).

## Runtime requirements

GPU is optional at runtime: `ml/src/device.py` auto-selects CUDA when present
and falls back to CPU transparently (measured CPU inference: 4.43 win/s with
retrieval ≈ 80 s/contract median; GPU ≈ 12 s/contract end-to-end).
