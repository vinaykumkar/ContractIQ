# ContractIQ — Phase 3 Model Selection

_Generated: 2026-08-30 · All candidate metadata verified via the Hugging Face Hub API before download._

## Candidates considered

| | `deepset/minilm-uncased-squad2` | `distilbert/distilbert-base-uncased-distilled-squad` | `deepset/roberta-base-squad2` |
|---|---|---|---|
| Task | extractive QA (SQuAD**2**) | extractive QA (SQuAD1) | extractive QA (SQuAD**2**) |
| Architecture | MiniLM — 6-layer BERT, hidden 384 | DistilBERT — 6-layer, hidden 768 | RoBERTa-base — 12-layer, hidden 768 |
| Parameters | 33.4M | 66.4M | 124.1M |
| Approx. size (fp32) | ~127 MB | ~253 MB | ~496 MB |
| License | CC-BY-4.0 (attribution given here) | Apache-2.0 | CC-BY-4.0 (attribution) |
| No-answer support | **Yes (SQuAD2-trained)** | No (SQuAD1: always predicts a span) | **Yes (SQuAD2-trained)** |
| CPU throughput (this machine, 128 real windows, 8 threads) | **4.43 win/s** (batch 8) | 3.41 win/s (batch 16) | not benchmarked — 3.7× the compute of MiniLM |
| Tokenizer | BERT uncased wordpiece (same vocabulary as Phase 2 features) | BERT uncased wordpiece | RoBERTa BPE — **incompatible with Phase 2 features**, would require full re-preprocessing |
| Tokenizer max length | 512 | 512 | 512 |

## Decision

**Primary model: `deepset/minilm-uncased-squad2` (FP32).**

Reasoning:

1. **Speed** — measured 1.48× faster than the Phase 2 DistilBERT smoke model on identical windows (4.43 vs 3.41 win/s), with half the memory footprint.
2. **No-answer awareness** — SQuAD2 training makes its `[CLS]` representation a usable no-answer signal; DistilBERT-squad (SQuAD1) always produces a span, which is structurally wrong for ContractIQ's `found: false` requirement.
3. **Feature compatibility** — BERT-uncased wordpiece means the 183k Phase 2 training windows remain valid for fine-tuning this checkpoint; RoBERTa would force a full re-preprocessing.
4. **RoBERTa-squad2** is the documented GPU accuracy alternative (bigger, likely stronger after fine-tuning) — `ml/src/train.py --model deepset/roberta-base-squad2` supports it directly, but it is not the local default.

"Legal"-named models were deliberately not chosen by name: publicly available legal-domain BERT checkpoints are rarely trained for extractive QA and would need exactly the fine-tuning this project already defines; the practical path is fine-tuning a QA-native architecture on CUAD.

## INT8 dynamic quantization — rejected

`torch.ao.quantization.quantize_dynamic` on Linear layers measured **1.24× faster** (5.48 vs 4.43 win/s) but changed the argmax best span on **56% of benchmark windows** (mean |Δ confidence| = 0.0126 — near-tie flips). Per the phase rules, quantization is rejected for the default pipeline; it remains reproducible from `scripts/phase3_benchmark.py`. The PyTorch 2.13 migration notice (torchao `quantize_` API) is noted for future work.

## Retrieval stage — adopted with per-clause fallback

TF-IDF block ranking (scikit-learn, fully local) with clause keyword lexicons + a 2-block title/preamble boost:

- **11 clauses** (audit rights, governing law, insurance, renewal term ≥ 95% recall; agreement date, anti-assignment, document name, effective date, expiration date, parties, termination for convenience 92–100%): retrieval with **top-K=15** blocks. Aggregate gold-answer recall at K=15: **95.2%**.
- **4 clauses** (non-compete 62%, exclusivity 91%, license grant 93%, cap on liability 88% at K=15): **full-document inference** — recall below the acceptance bar, and answer loss is unacceptable.

Measurement details and the K sweep: `reports/phase3_retrieval_recall.{json,md}`. Strategy is stored centrally in `ml/configs/model.json`.

## End-to-end speed model (measured inputs)

| Scenario | Phase 2 (DistilBERT, full doc) | Phase 3 (MiniLM, retrieval) |
|---|---:|---:|
| Throughput | 3.0 win/s | 4.43 win/s |
| Median contract (436 windows full-doc) | ~204 s | ~62 s estimated (275 windows) |
| p95 contract (1,456 windows) | ~680 s | ~130 s estimated |
| Longest contract (2,266 windows) | ~1,059 s | ~180 s estimated |

Final confirmed numbers come from the calibrated end-to-end benchmark (`reports/phase3_evaluation.md`) — never from these estimates alone.
