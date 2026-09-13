# ContractIQ — Phase 3 GPU Benchmark

_Generated: 2026-08-30T16:46:54.566540+00:00_ · `deepset/minilm-uncased-squad2` (CC-BY-4.0, fp32) · NVIDIA GeForce RTX 2050 (4.29 GB, CUDA 13.0)

| Batch | Windows/s | ms/window | Peak VRAM (GB) |
|---:|---:|---:|---:|
| 8 | 52.8 | 18.93 | 0.21 |
| 16 | 24.7 | 40.48 | 0.28 |
| 32 | 17.8 | 56.03 | 0.43 |
| 64 | 29.6 | 33.8 | 0.71 |

Best: **52.8 win/s at batch 8** vs CPU 4.43 win/s → **11.9× speedup**.

Whole-contract estimates (model time only):

| Scenario | Windows | Estimated |
|---|---:|---:|
| median contract | 436 | ~8.3s |
| p95 contract | 1456 | ~27.6s |
| longest contract | 2266 | ~42.9s |