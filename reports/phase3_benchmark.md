# ContractIQ — Phase 3 CPU Model Benchmark

_Generated: 2026-08-30T14:51:32.686339+00:00_ · 8 cores · torch threads 8 · 128 real windows from validation features

| Variant | Best batch | Windows/s | ms/window |
|---|---:|---:|---:|
| distilbert-squad-fp32 | 16 | 3.41 | 293.2 |
| minilm-squad2-fp32 | 8 | 4.43 | 225.7 |
| minilm-squad2-int8 | 2 | 5.48 | 182.4 |

INT8 output agreement: 56/128 identical best spans (43.8%), mean |Δconfidence| = 0.012585


## Per-batch throughput (windows/s)

| Batch | distilbert-squad-fp32 | minilm-squad2-fp32 | minilm-squad2-int8 |
|---|---:|---:|---:|
| 1 | 1.2 | 4.02 | 5.23 |
| 2 | 0.75 | 4.15 | 5.48 |
| 4 | 0.84 | 4.0 | 3.93 |
| 8 | 1.18 | 4.43 | 4.51 |
| 16 | 3.41 | 4.41 | 4.64 |

Peak RSS during benchmark: 1.15 GB
