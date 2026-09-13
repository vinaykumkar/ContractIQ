# ContractIQ — Phase 2 CPU Benchmark

_Generated: 2026-08-30T14:41:43.267163+00:00_ · Model: `distilbert/distilbert-base-uncased-distilled-squad` (Apache-2.0, ~66M params) · CPU only

CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel · 8 physical / 12 logical cores · torch threads 8 · RAM 16.8 GB

## Measured throughput (128 real windows, forward pass)

| Batch size | Windows/s | ms/window |
|---:|---:|---:|
| 1 | 2.04 | 490.8 |
| 2 | 1.99 | 502.6 |
| 4 | 2.14 | 466.4 |
| 8 | 2.13 | 469.4 |

Thread experiment (batch 4): 4 threads → 2.68 win/s, 8 threads → 2.99 win/s

## Whole-contract estimates (15 clauses)

| Scenario | Windows | Estimated time |
|---|---:|---:|
| median contract | 436 | ~203.7s |
| p95 contract | 1456 | ~680.4s |
| longest contract | 2266 | ~1058.9s |

Peak RSS during benchmark: 0.88 GB

- Forward pass only: tokenization is a one-time cost per contract (context tokenized once per contract, reused across all clauses).
- Estimates extrapolate the measured windows/second linearly; real analysis adds span decoding (small) and Python overhead.
- These are SMOKE/benchmark numbers, not model quality metrics.