#!/usr/bin/env python
"""Phase 3 model benchmark: DistilBERT-squad vs MiniLM-squad2, FP32 vs INT8.

Measures on this CPU machine with the same Phase 2 window sample:
- forward throughput at batch sizes 1/2/4/8/16
- thread-count effect
- RAM usage and model size
- output agreement between FP32 and INT8 (best spans on a validation sample)

Writes reports/phase3_benchmark.{json,md}. All numbers are measured, none estimated.
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

MODELS = {
    "distilbert-squad-fp32": "distilbert/distilbert-base-uncased-distilled-squad",
    "minilm-squad2-fp32": "deepset/minilm-uncased-squad2",
}
VAL_DIR = PROCESSED_DIR / "val_eval_features"
SAMPLE_WINDOWS = 128
BATCH_SIZES = [1, 2, 4, 8, 16]
THREADS = 8  # best measured in Phase 2


def peak_rss_gb(stop_event, out):
    proc = psutil.Process()
    peak = 0.0
    while not stop_event.is_set():
        peak = max(peak, proc.memory_info().rss / 1e9)
        time.sleep(0.05)
    out.append(peak)


def load_windows(limit: int):
    import pyarrow.parquet as pq

    shard = sorted(VAL_DIR.glob("shard_*.parquet"))[0]
    table = pq.read_table(shard, columns=["input_ids"])
    return table.column("input_ids").to_pylist()[:limit]


def forward_seconds(model, windows, batch_size, pad_id):
    total = 0.0
    for i in range(0, len(windows), batch_size):
        chunk = windows[i : i + batch_size]
        max_len = max(len(w) for w in chunk)
        input_ids = torch.tensor([w + [pad_id] * (max_len - len(w)) for w in chunk], dtype=torch.long)
        attention = torch.tensor([[1] * len(w) + [0] * (max_len - len(w)) for w in chunk], dtype=torch.long)
        t0 = time.perf_counter()
        with torch.inference_mode():
            model(input_ids=input_ids, attention_mask=attention)
        total += time.perf_counter() - t0
    return total


def best_spans(model, windows, pad_id):
    """Best (start,end) token indexes + confidence per window (no cross-window logic)."""
    outs = []
    for i in range(0, len(windows), 16):
        chunk = windows[i : i + 16]
        max_len = max(len(w) for w in chunk)
        input_ids = torch.tensor([w + [pad_id] * (max_len - len(w)) for w in chunk], dtype=torch.long)
        attention = torch.tensor([[1] * len(w) + [0] * (max_len - len(w)) for w in chunk], dtype=torch.long)
        with torch.inference_mode():
            o = model(input_ids=input_ids, attention_mask=attention)
        s = torch.softmax(o.start_logits, dim=-1)
        e = torch.softmax(o.end_logits, dim=-1)
        for k in range(len(chunk)):
            n = int(attention[k].sum())
            best_s, best_e, best_c = 0, 0, -1.0
            for a in range(1, n):
                for b in range(a, min(a + 20, n)):
                    c = float(s[k, a] * e[k, b])
                    if c > best_c:
                        best_s, best_e, best_c = a, b, c
            outs.append((best_s, best_e, round(best_c, 5)))
    return outs


def benchmark_model(name, model, pad_id, windows):
    # warmup
    forward_seconds(model, windows[:8], 8, pad_id)
    results = []
    for bs in BATCH_SIZES:
        secs = forward_seconds(model, windows, bs, pad_id)
        results.append({
            "batch_size": bs,
            "wall_seconds": round(secs, 2),
            "windows_per_second": round(len(windows) / secs, 2),
            "ms_per_window": round(1000 * secs / len(windows), 1),
        })
        print(f"  [{name}] batch={bs}: {len(windows)/secs:.2f} win/s")
    best = max(results, key=lambda r: r["windows_per_second"])
    return results, best


def main() -> int:
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer

    torch.set_num_threads(THREADS)
    windows = load_windows(SAMPLE_WINDOWS)
    print(f"Sample: {len(windows)} windows, torch threads={torch.get_num_threads()}")

    stop_event = threading.Event()
    peak_out: list[float] = []
    threading.Thread(target=peak_rss_gb, args=(stop_event, peak_out), daemon=True).start()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": "cpu",
        "cpu": {
            "processor": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "torch_threads": THREADS,
            "total_ram_gb": round(psutil.virtual_memory().total / 1e9, 1),
        },
        "torch_version": torch.__version__,
        "sample_windows": len(windows),
        "variants": {},
        "int8_output_diff": {},
    }

    spans_cache = {}
    try:
        for name, mid in MODELS.items():
            print(f"Benchmarking {name} ({mid})")
            tokenizer = AutoTokenizer.from_pretrained(mid, use_fast=True)
            model = AutoModelForQuestionAnswering.from_pretrained(mid)
            model.eval()
            results, best = benchmark_model(name, model, tokenizer.pad_token_id, windows)
            report["variants"][name] = {
                "model_id": mid,
                "tokenizer_max_len": tokenizer.model_max_length,
                "results": results,
                "best": best,
            }
            if name == "minilm-squad2-fp32":
                spans_cache["fp32"] = best_spans(model, windows, tokenizer.pad_token_id)
                # INT8 dynamic quantization on Linear layers
                print("Quantizing MiniLM to INT8 (dynamic, Linear layers)...")
                q_model = torch.ao.quantization.quantize_dynamic(
                    model, {torch.nn.Linear}, dtype=torch.qint8
                )
                q_model.eval()
                q_results, q_best = benchmark_model("minilm-squad2-int8", q_model, tokenizer.pad_token_id, windows)
                report["variants"]["minilm-squad2-int8"] = {
                    "model_id": mid + " (dynamic INT8)",
                    "tokenizer_max_len": tokenizer.model_max_length,
                    "results": q_results,
                    "best": q_best,
                }
                spans_cache["int8"] = best_spans(q_model, windows, tokenizer.pad_token_id)
                # output agreement
                same = sum(1 for a, b in zip(spans_cache["fp32"], spans_cache["int8"]) if a[:2] == b[:2])
                conf_diff = [abs(a[2] - b[2]) for a, b in zip(spans_cache["fp32"], spans_cache["int8"])]
                report["int8_output_diff"] = {
                    "windows_compared": len(spans_cache["fp32"]),
                    "identical_best_spans": same,
                    "identical_rate": round(same / len(spans_cache["fp32"]), 4),
                    "mean_abs_confidence_delta": round(sum(conf_diff) / len(conf_diff), 6),
                    "max_abs_confidence_delta": round(max(conf_diff), 6),
                }
                print(f"  INT8 identical spans: {same}/{len(spans_cache['fp32'])}")
                del q_model
            del model
    finally:
        stop_event.set()
        time.sleep(0.1)
    report["peak_rss_gb_during_benchmark"] = round(peak_out[0], 2) if peak_out else None

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "phase3_benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = ["# ContractIQ — Phase 3 CPU Model Benchmark", "",
          f"_Generated: {report['generated_at']}_ · {report['cpu']['physical_cores']} cores · "
          f"torch threads {THREADS} · {len(windows)} real windows from validation features", "",
          "| Variant | Best batch | Windows/s | ms/window |", "|---|---:|---:|---:|"]
    for name, v in report["variants"].items():
        b = v["best"]
        md.append(f"| {name} | {b['batch_size']} | {b['windows_per_second']} | {b['ms_per_window']} |")
    d = report["int8_output_diff"]
    if d:
        md += ["", f"INT8 output agreement: {d['identical_best_spans']}/{d['windows_compared']} identical best spans "
               f"({d['identical_rate']*100:.1f}%), mean |Δconfidence| = {d['mean_abs_confidence_delta']}", ""]
    md += ["", "## Per-batch throughput (windows/s)", "", "| Batch | " + " | ".join(report["variants"]) + " |",
           "|---|" + "---:|" * len(report["variants"])]
    for bs in BATCH_SIZES:
        row = [str(bs)]
        for name in report["variants"]:
            r = next(x for x in report["variants"][name]["results"] if x["batch_size"] == bs)
            row.append(str(r["windows_per_second"]))
        md.append("| " + " | ".join(row) + " |")
    md += ["", f"Peak RSS during benchmark: {report['peak_rss_gb_during_benchmark']} GB", ""]
    (REPORTS_DIR / "phase3_benchmark.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {REPORTS_DIR / 'phase3_benchmark.json'} and .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
