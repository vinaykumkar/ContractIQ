#!/usr/bin/env python
"""Phase 3 GPU benchmark: MiniLM QA on CUDA with the same fixed window sample
used for the CPU benchmarks (128 real windows from the validation features).

Records windows/sec and VRAM for batch sizes 8/16/32/64 (stops increasing if
VRAM usage becomes unsafe), and estimates whole-contract inference time vs the
measured CPU baseline. Writes reports/phase3_gpu_benchmark.{json,md}.
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

from ml.src.config import PROCESSED_DIR, REPORTS_DIR  # noqa: E402
from ml.src.device import get_device  # noqa: E402

MODEL_ID = "deepset/minilm-uncased-squad2"
VAL_DIR = PROCESSED_DIR / "val_eval_features"
SAMPLE_WINDOWS = 128
BATCH_SIZES = [8, 16, 32, 64]
VRAM_SAFETY_FRACTION = 0.90  # stop growing batches above 90% VRAM


def load_windows(limit: int):
    import pyarrow.parquet as pq

    shard = sorted(VAL_DIR.glob("shard_*.parquet"))[0]
    table = pq.read_table(shard, columns=["input_ids"])
    return table.column("input_ids").to_pylist()[:limit]


def forward_seconds(model, windows, batch_size, pad_id, device):
    total = 0.0
    for i in range(0, len(windows), batch_size):
        chunk = windows[i : i + batch_size]
        max_len = max(len(w) for w in chunk)
        input_ids = torch.tensor([w + [pad_id] * (max_len - len(w)) for w in chunk],
                                 dtype=torch.long)
        attention = torch.tensor([[1] * len(w) + [0] * (max_len - len(w)) for w in chunk],
                                 dtype=torch.long)
        input_ids = input_ids.to(device, non_blocking=True)
        attention = attention.to(device, non_blocking=True)
        if device.type == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        with torch.inference_mode():
            model(input_ids=input_ids, attention_mask=attention)
        if device.type == "cuda":
            torch.cuda.synchronize()
        total += time.perf_counter() - t0
    return total


def main() -> int:
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer

    device = get_device()
    if device.type != "cuda":
        print("CUDA is not available - GPU benchmark cannot run.")
        return 1

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=True)
    model = AutoModelForQuestionAnswering.from_pretrained(MODEL_ID).to(device)
    model.eval()
    pad_id = tokenizer.pad_token_id
    windows = load_windows(SAMPLE_WINDOWS)

    torch.cuda.reset_peak_memory_stats()
    forward_seconds(model, windows[:16], 8, pad_id, device)  # warmup

    results = []
    vram_limit = torch.cuda.get_device_properties(0).total_memory * VRAM_SAFETY_FRACTION
    for bs in BATCH_SIZES:
        secs = forward_seconds(model, windows, bs, pad_id, device)
        wps = len(windows) / secs
        peak = torch.cuda.max_memory_allocated() / 1e9
        results.append({
            "batch_size": bs,
            "wall_seconds": round(secs, 3),
            "windows_per_second": round(wps, 1),
            "ms_per_window": round(1000 * secs / len(windows), 2),
            "peak_vram_gb": round(peak, 2),
        })
        print(f"batch={bs}: {wps:.1f} win/s | peak VRAM {peak:.2f} GB", flush=True)
        if peak > vram_limit:
            print(f"peak VRAM {peak:.2f} GB exceeds safety threshold - not increasing batch size further")
            break

    best = max(results, key=lambda r: r["windows_per_second"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": {"id": MODEL_ID, "license": "cc-by-4.0", "parameters": "~33.4M fp32"},
        "gpu": {
            "name": torch.cuda.get_device_name(0),
            "total_vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2),
            "cuda_runtime": torch.version.cuda,
        },
        "torch_version": torch.__version__,
        "sample_windows": len(windows),
        "batch_results": results,
        "best": best,
        "cpu_reference": {
            "source": "reports/phase3_benchmark.json (same 128-window sample)",
            "minilm_fp32_best_windows_per_second": 4.43,
        },
        "notes": [
            "Timings include host->device transfer and CUDA synchronization.",
            "Whole-contract estimates include CPU-side tokenization/retrieval "
            "overhead that GPU speedups do not remove.",
        ],
    }

    # per-contract estimates using Phase 2 measured window counts
    for name, wins in [("median_contract", 436), ("p95_contract", 1456), ("longest_contract", 2266)]:
        report[f"{name}_estimate_seconds"] = round(wins / best["windows_per_second"], 1)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "phase3_gpu_benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = ["# ContractIQ — Phase 3 GPU Benchmark", "",
          f"_Generated: {report['generated_at']}_ · `{MODEL_ID}` (CC-BY-4.0, fp32) · "
          f"{report['gpu']['name']} ({report['gpu']['total_vram_gb']} GB, CUDA {report['gpu']['cuda_runtime']})", "",
          "| Batch | Windows/s | ms/window | Peak VRAM (GB) |", "|---:|---:|---:|---:|"]
    for r in results:
        md.append(f"| {r['batch_size']} | {r['windows_per_second']} | {r['ms_per_window']} | {r['peak_vram_gb']} |")
    md += ["",
           f"Best: **{best['windows_per_second']} win/s at batch {best['batch_size']}** "
           f"vs CPU 4.43 win/s → **{round(best['windows_per_second'] / 4.43, 1)}× speedup**.", "",
           "Whole-contract estimates (model time only):", "",
           "| Scenario | Windows | Estimated |", "|---|---:|---:|"]
    for name in ["median_contract", "p95_contract", "longest_contract"]:
        md.append(f"| {name.replace('_', ' ')} | {[436, 1456, 2266][['median_contract','p95_contract','longest_contract'].index(name)]} "
                  f"| ~{report[f'{name}_estimate_seconds']}s |")
    (REPORTS_DIR / "phase3_gpu_benchmark.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {REPORTS_DIR / 'phase3_gpu_benchmark.json'} and .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
