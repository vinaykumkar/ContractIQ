#!/usr/bin/env python
"""Phase 2 CPU batching benchmark with the actual smoke-test model.

Measures real forward-pass throughput (windows/second) at batch sizes 1/2/4/8
on windows sampled from the prepared validation features, then extrapolates to
whole-contract analysis scenarios (median / p95 / longest, 15 clauses each).

Writes reports/phase2_benchmark.{json,md}. No fake numbers: everything is
measured on this machine with torch.inference_mode() and model.eval().
"""
from __future__ import annotations

import json
import platform
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.src.config import PROCESSED_DIR, REPORTS_DIR  # noqa: E402

MODEL_ID = "distilbert/distilbert-base-uncased-distilled-squad"
VAL_DIR = PROCESSED_DIR / "val_eval_features"
SAMPLE_WINDOWS = 128
WARMUP_WINDOWS = 8
BATCH_SIZES = [1, 2, 4, 8]


def peak_rss_gb(stop_event, out):
    proc = psutil.Process()
    peak = 0.0
    while not stop_event.is_set():
        peak = max(peak, proc.memory_info().rss / 1e9)
        time.sleep(0.05)
    out.append(peak)


def load_windows(limit: int) -> list[list[int]]:
    import pyarrow.parquet as pq

    shard = sorted(VAL_DIR.glob("shard_*.parquet"))[0]
    table = pq.read_table(shard, columns=["input_ids"])
    rows = table.column("input_ids").to_pylist()[:limit]
    return rows


def forward_seconds(model, windows, batch_size, pad_id):
    total = 0.0
    for i in range(0, len(windows), batch_size):
        chunk = windows[i : i + batch_size]
        max_len = max(len(w) for w in chunk)
        input_ids = torch.tensor(
            [w + [pad_id] * (max_len - len(w)) for w in chunk], dtype=torch.long
        )
        attention = torch.tensor(
            [[1] * len(w) + [0] * (max_len - len(w)) for w in chunk], dtype=torch.long
        )
        t0 = time.perf_counter()
        with torch.inference_mode():
            model(input_ids=input_ids, attention_mask=attention)
        total += time.perf_counter() - t0
    return total


def main() -> int:
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased", use_fast=True)
    model = AutoModelForQuestionAnswering.from_pretrained(MODEL_ID)
    model.eval()
    pad_id = tokenizer.pad_token_id

    windows = load_windows(SAMPLE_WINDOWS)
    assert len(windows) >= SAMPLE_WINDOWS
    print(f"Loaded {len(windows)} windows from {VAL_DIR.name}")

    # warmup
    forward_seconds(model, windows[:WARMUP_WINDOWS], 4, pad_id)

    stop_event = threading.Event()
    peak_out: list[float] = []
    monitor = threading.Thread(target=peak_rss_gb, args=(stop_event, peak_out), daemon=True)
    monitor.start()

    results = []
    default_threads = torch.get_num_threads()
    for bs in BATCH_SIZES:
        secs = forward_seconds(model, windows, bs, pad_id)
        wps = len(windows) / secs
        results.append({
            "batch_size": bs,
            "windows": len(windows),
            "wall_seconds": round(secs, 3),
            "windows_per_second": round(wps, 2),
            "ms_per_window": round(1000 * secs / len(windows), 1),
        })
        print(f"batch={bs}: {secs:.2f}s for {len(windows)} windows -> {wps:.1f} win/s")

    # thread-count experiment at the best batch size
    best_bs = max(results, key=lambda r: r["windows_per_second"])["batch_size"]
    thread_results = []
    for threads in sorted({default_threads, max(1, default_threads // 2)}):
        torch.set_num_threads(threads)
        secs = forward_seconds(model, windows, best_bs, pad_id)
        thread_results.append({
            "torch_threads": threads,
            "batch_size": best_bs,
            "windows_per_second": round(len(windows) / secs, 2),
        })
        print(f"threads={threads}: {len(windows)/secs:.1f} win/s")
    torch.set_num_threads(default_threads)
    stop_event.set()
    monitor.join(timeout=1)

    # per-contract window totals from val features (15 clauses per contract)
    import pyarrow.parquet as pq
    import collections

    counts = collections.Counter()
    for shard in sorted(VAL_DIR.glob("shard_*.parquet")):
        t = pq.read_table(shard, columns=["contract_id"])
        counts.update(t.column("contract_id").to_pylist())
    totals = sorted(counts.values())
    def p(q):
        return totals[min(len(totals) - 1, int(q / 100 * (len(totals) - 1)))]
    contract_scenarios = {
        "median_windows_per_contract": p(50),
        "p95_windows_per_contract": p(95),
        "max_windows_per_contract": totals[-1],
        "contracts_observed": len(totals),
    }

    best = max(results, key=lambda r: r["windows_per_second"])
    scenarios = {}
    for name, key in [("median", "median_windows_per_contract"),
                      ("p95", "p95_windows_per_contract"),
                      ("longest", "max_windows_per_contract")]:
        w = contract_scenarios[key]
        scenarios[name] = {
            "windows": w,
            "estimated_seconds_at_best_batch": round(w / best["windows_per_second"], 1),
        }
        print(f"{name} contract: {w} windows -> ~{w/best['windows_per_second']:.0f}s")

    cpu = {
        "processor": platform.processor(),
        "machine": platform.machine(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "torch_default_threads": default_threads,
        "total_ram_gb": round(psutil.virtual_memory().total / 1e9, 1),
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": {"id": MODEL_ID, "license": "apache-2.0", "parameters": "~66.4M fp32"},
        "device": "cpu",
        "torch_version": torch.__version__,
        "cpu": cpu,
        "sample": {"windows": SAMPLE_WINDOWS, "source": "val_eval_features shard 0"},
        "batch_results": results,
        "thread_experiment": thread_results,
        "contract_scenarios_windows": contract_scenarios,
        "whole_contract_estimates": scenarios,
        "peak_rss_gb_during_benchmark": round(peak_out[0], 2) if peak_out else None,
        "notes": [
            "Forward pass only: tokenization is a one-time cost per contract "
            "(context tokenized once per contract, reused across all clauses).",
            "Estimates extrapolate the measured windows/second linearly; "
            "real analysis adds span decoding (small) and Python overhead.",
            "These are SMOKE/benchmark numbers, not model quality metrics.",
        ],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "phase2_benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = ["# ContractIQ — Phase 2 CPU Benchmark", "",
          f"_Generated: {report['generated_at']}_ · Model: `{MODEL_ID}` (Apache-2.0, ~66M params) · CPU only", "",
          f"CPU: {cpu['processor'] or 'unknown'} · {cpu['physical_cores']} physical / {cpu['logical_cores']} logical cores · "
          f"torch threads {cpu['torch_default_threads']} · RAM {cpu['total_ram_gb']} GB", "",
          "## Measured throughput (128 real windows, forward pass)", "",
          "| Batch size | Windows/s | ms/window |", "|---:|---:|---:|"]
    for r in results:
        md.append(f"| {r['batch_size']} | {r['windows_per_second']} | {r['ms_per_window']} |")
    md += ["", f"Thread experiment (batch {best_bs}): "
           + ", ".join(f"{t['torch_threads']} threads → {t['windows_per_second']} win/s"
                       for t in thread_results), "",
          "## Whole-contract estimates (15 clauses)", "",
          "| Scenario | Windows | Estimated time |", "|---|---:|---:|"]
    for name, s in scenarios.items():
        md.append(f"| {name} contract | {s['windows']} | ~{s['estimated_seconds_at_best_batch']}s |")
    md += ["", f"Peak RSS during benchmark: {report['peak_rss_gb_during_benchmark']} GB", ""]
    for n in report["notes"]:
        md.append(f"- {n}")
    (REPORTS_DIR / "phase2_benchmark.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {REPORTS_DIR / 'phase2_benchmark.json'} and .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
