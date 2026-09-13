# ContractIQ — ML Model

## Dataset

**CUAD v1** (Contract Understanding Atticus Dataset, Henriksson et al. 2021) —
510 real US commercial contracts, 41 legal-clause categories, 20,910 QA pairs.
Supplied as `data.zip` (immutable, checksum-guarded in `data/DATA_INTEGRITY.txt`).

Split: 408 official training contracts (deterministic 90/10 contract-level
split → 367 train / 41 validation) and the untouched 102-contract official
test set. `data.zip`/`data/raw`/`data/processed` are **training assets** — the
finished app does not need them to run.

## Version-1 enabled clauses (15 of 41)

Document Name, Parties, Agreement Date, Effective Date, Expiration Date,
Renewal Term, Governing Law, Termination for Convenience, Non-Compete,
Exclusivity, Anti-Assignment, License Grant, Audit Rights, Cap on Liability,
Insurance. The full registry with the exact CUAD question templates lives in
`ml/configs/clauses.json`.

## Task formulation

Extractive question answering: `question + contract text → answer span or no
answer`. Long contracts (median ≈ 6.7k tokens, max ≈ 78.6k) are handled with
overlapping sliding windows (512 tokens, stride 128). The training file
explodes each gold span into its own QA instance; evaluation compares against
all gold spans with SQuAD normalization.

## Model

- Base: `deepset/minilm-uncased-squad2` — MiniLM (6-layer BERT), 33.4M
  parameters, ~127 MB, **CC-BY-4.0**, SQuAD2 no-answer aware, BERT-uncased
  tokenizer compatible with the Phase 2 features.
- Bundled fine-tuned model: `ml/models/final/` (weights + tokenizer + config +
  `training_meta.json`).
- Selected over DistilBERT-squad (3.41 win/s, no no-answer training) and
  RoBERTa-squad2 (accurate but 3.7× compute + different tokenizer). Details:
  `reports/phase3_model_selection.md`.

## Fine-tuning

One GPU epoch over 20,420 windows (5,105 positives + 15,315 seeded negatives,
ratio 1:3), batch 16, lr 3e-5, AMP fp16, 1,277 steps in **838 s** on an RTX
2050. Exact command in `reports/phase3_training.md`. The GPU path saves the
best checkpoint to `ml/models/final/`; a CPU "tiny" proof mode
(`python -m ml.src.train --tiny`) is strictly time/step limited.

## Confidence thresholding

Thresholds (`no_answer_delta`, `min_confidence`) are calibrated on the
**validation split only** via `scripts/calibrate_thresholds.py` and frozen in
`ml/configs/model.json`. The official test set was evaluated exactly once with
frozen settings: **overall EM 60.8% / F1 66.2%** (`reports/phase3_test_evaluation.md`).

## Retrieval optimization

TF-IDF block ranking (scikit-learn, fully local) with clause keyword lexicons
narrows 11 clauses to the top-15 blocks (measured gold-answer recall 95.2%);
4 clauses fall back to full-document inference because their recall was too
low. Result: median contract analysis ≈ 4–12 s GPU / ~80 s CPU.

## GPU / CPU inference

`ml/src/device.py` picks CUDA when available (model stays resident between
requests); otherwise CPU. INT8 quantization was benchmarked and **rejected**
(1.24× speedup, 56% argmax span flips).

If the installed NVIDIA driver cannot run the bundled CUDA build
(`torch.cuda.is_available()` is False), the analyzer runs on CPU with eager
attention and stubs out torch's CUDA stream-capture probe — without this,
transformers' attention-mask code can crash the process (access violation) on
a CUDA-built torch with an incompatible driver (fixed in `ml/src/inference.py`).

## Important scope statement

**CUAD does NOT provide legal risk labels.** The model only extracts clauses.
Risk scoring is a separate, transparent heuristic engine
(`backend/app/risk/`) — see `docs/RISK_SCORING.md`.
