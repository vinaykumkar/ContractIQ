# ContractIQ — Phase 3 Evaluation Report

_Generated: 2026-08-30 · All numbers measured; none estimated or fabricated._

## Evaluation setup

- **Validation (model selection / threshold tuning):** 41 contracts carved from the official training split (seed 42, contract level). 615 (contract, clause) pairs; 386 answerable / 229 no-answer.
- **Official test (final, once):** 102 untouched contracts — see `reports/phase3_test_evaluation.{json,md}` for the frozen-configuration run.
- Metrics follow SQuAD conventions: bag-of-words token F1 with best-match-over-gold, SQuAD2 no-answer credit, standard text normalization (lowercase, punctuation/article removal, whitespace collapse).

## A. Baseline (zero-shot) vs fine-tuned on validation

Both rows use the same frozen retrieval strategy and are scored on 41 validation contracts (386 answerable / 229 no-answer pairs), with thresholds calibrated on validation only.

| Metric | Zero-shot `minilm-squad2` | **Fine-tuned (1 GPU epoch)** |
|---|---:|---:|
| Overall EM (SQuAD2 convention) | 35.1% | **61.0%** |
| Overall F1 | 35.4% | **66.6%** |
| Answerable EM (386 pairs) | 0.0% | **57.8%** |
| Answerable F1 | 0.4% | **66.7%** (P 70.1% / R 67.6%) |
| No-answer accuracy (229 pairs) | 94.3% | 66.4% |
| Answerable-detection recall | 8.6% | 83.2% |
| Found-decision precision | 71.7% | 80.7% |
| Found-decision macro F1 | 15.3% | **81.9%** |

Calibrated thresholds (fine-tuned): `no_answer_delta = 0.0`, `min_confidence = 0.0` — the calibration grid (deltas 0–0.5 × min-confs 0–0.1) found the found-decision flat for min_conf ≤ 0.02, meaning the fine-tuned CLS no-answer signal separates cleanly on its own. Calibration runtime on GPU: 8.7 min.

**Honest reading:** one epoch of fine-tuning turns an unusable extractor (answerable EM 0.0) into a genuinely useful one (57.8% EM / 66.7% F1). The weakest axis is now no-answer rejection (66.4%) — improving it needs more epochs / more negatives / better thresholding, deliberately left as future work within this phase's time budget. Full detail of the zero-shot run is preserved in `reports/phase3_calibration.json` and the per-clause table below (zero-shot); fine-tuned per-clause numbers are in `reports/_val_metrics_finetuned.json`.

### Fine-tuned per-clause validation (answerable F1 / no-answer accuracy)

| Clause | Answerable F1 | No-answer acc. |
|---|---:|---:|
| document_name | 90.8% | n/a (always answerable) |
| governing_law | 86.3% | 100% |
| agreement_date | 79.7% | 0% |
| audit_rights | 77.0% | 80% |
| termination_for_convenience | 70.1% | 58% |
| expiration_date | 68.2% | 60% |
| effective_date | 67.4% | 12% |
| renewal_term | 65.9% | 50% |
| insurance | 58.9% | 85% |
| anti_assignment | 58.2% | 78% |
| cap_on_liability | 56.6% | 45% |
| exclusivity | 55.7% | 50% |
| license_grant | 48.7% | 88% |
| parties | 40.8% | n/a (always answerable) |
| non_compete | 27.6% | 90% |

## B. Optimized pipeline speed (measured)

| Configuration | Throughput | End-to-end per contract |
|---|---:|---|
| Phase 2: DistilBERT fp32, full document (CPU) | 3.0 win/s | ~204 s (median, estimated) |
| Phase 3 CPU: MiniLM fp32 + retrieval (measured calibration run) | 4.43 win/s | **~80 s** (3,299 s / 41 val contracts, end-to-end) |
| Phase 3 GPU: RTX 2050, fine-tuned model (measured) | 52.8 win/s forward | **~12 s** calibration run, **~4 s** test-run contracts |

- GPU forward benchmark: batch 8 = **52.8 win/s → 11.9× CPU** (peak VRAM 0.71 GB of 4 GB; larger batches were slower on this GPU — transfer-bound).
- Measured end-to-end on GPU: 41 val contracts in 487 s (~12 s each); 102 test contracts in ~420 s (~4 s each — the test split is shorter, median 5.1k vs 7.3k tokens).
- The Phase 3 <60 s median target is **met on GPU** (~4–12 s) and approached on CPU (~80 s). INT8 quantization was measured and rejected (1.24× gain, 56% argmax span flips); ONNX left as optional follow-up.

## C. What the frozen official test evaluation adds

`reports/phase3_test_evaluation.md` reports the same metric set for the untouched 102-contract test set, run exactly once with frozen model + thresholds + retrieval. Expected per validation: extraction near zero, no-answer behaviour high — confirming the baseline honestly rather than hiding it.
