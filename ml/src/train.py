"""Training pipeline for ContractIQ extractive QA (CPU tiny runs + full GPU).

Single entry point used for BOTH paths (same code, different scale):

    # PATH A - local practical baseline (tiny CPU proof, minutes):
    python -m ml.src.train --tiny

    # PATH B - full fine-tune on a CUDA machine (hours):
    python -m ml.src.train --model deepset/minilm-uncased-squad2 --epochs 2 \
        --batch-size 16 --learning-rate 3e-5 --output ml/models/final

Data: Phase 2 Parquet features (data/processed/train_features). The official
test set is never referenced. Negative windows (97.2% of all windows) are
subsampled with a configurable positive:negative ratio, seeded and
reproducible; sampling statistics are logged and saved with checkpoints.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset

from .config import PROCESSED_DIR, PROJECT_ROOT
from .device import get_device

DEFAULT_BASELINE = "deepset/minilm-uncased-squad2"
TRAIN_DIR = PROCESSED_DIR / "train_features"


# ----------------------------------------------------------------- dataset

class WindowDataset(Dataset):
    """Thin wrapper over in-memory sampled feature rows (lists of ints)."""

    def __init__(self, rows: list[dict]):
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict:
        return self.rows[idx]


def load_train_table(limit: int | None = None) -> list[dict]:
    """Read all train shards (optionally capped) into RAM as light dicts.

    A full pass is ~183k rows; only call with sampled columns needed here.
    For the tiny run the caller samples first, so RAM stays bounded.
    """
    import pyarrow.parquet as pq

    rows: list[dict] = []
    files = sorted(TRAIN_DIR.glob("shard_*.parquet"))
    if not files:
        raise FileNotFoundError(
            f"No training features under {TRAIN_DIR}. Run scripts/prepare_phase2_data.py first."
        )
    for f in files:
        t = pq.read_table(f)
        cols = {c: t.column(c).to_pylist() for c in t.column_names}
        n = t.num_rows
        for i in range(n):
            rows.append({c: cols[c][i] for c in t.column_names})
            if limit and len(rows) >= limit:
                return rows
    return rows


def sample_train_rows(
    all_rows: list[dict],
    negative_ratio: float = 3.0,
    sample_limit: int | None = None,
    seed: int = 42,
) -> tuple[list[dict], dict]:
    """Keep all positive windows + a seeded sample of no-answer windows.

    negative_ratio: negatives kept per positive window (window-level).
    sample_limit: optional cap on TOTAL rows (applied after ratio sampling).
    Returns (rows, sampling_stats). Reproducible for a given seed + data.
    """
    rng = random.Random(seed)
    positives = [r for r in all_rows if not r["is_no_answer"]]
    negatives = [r for r in all_rows if r["is_no_answer"]]
    n_neg = min(len(negatives), int(round(len(positives) * negative_ratio)))
    neg_sample = rng.sample(negatives, n_neg) if n_neg < len(negatives) else list(negatives)
    rows = positives + neg_sample
    rng.shuffle(rows)
    stats = {
        "seed": seed,
        "negative_ratio": negative_ratio,
        "positives_available": len(positives),
        "negatives_available": len(negatives),
        "positives_kept": len(positives),
        "negatives_kept": len(neg_sample),
        "total_rows": len(rows),
        "shuffled": True,
    }
    if sample_limit and len(rows) > sample_limit:
        rows = rows[:sample_limit]
        stats["sample_limit"] = sample_limit
        stats["total_rows_after_limit"] = len(rows)
    return rows, stats


def collate(batch: list[dict], pad_id: int) -> dict:
    """Pad variable-length input_ids to the batch max; all labels to tensors."""
    max_len = max(len(b["input_ids"]) for b in batch)
    input_ids = torch.full((len(batch), max_len), pad_id, dtype=torch.long)
    attention = torch.zeros((len(batch), max_len), dtype=torch.long)
    for i, b in enumerate(batch):
        n = len(b["input_ids"])
        input_ids[i, :n] = torch.tensor(b["input_ids"], dtype=torch.long)
        attention[i, :n] = 1
    return {
        "input_ids": input_ids,
        "attention_mask": attention,
        "start_positions": torch.tensor([b["start_position"] for b in batch], dtype=torch.long),
        "end_positions": torch.tensor([b["end_position"] for b in batch], dtype=torch.long),
    }


# ----------------------------------------------------------------- training

def evaluate_quick(model, val_rows: list[dict], pad_id: int, device: torch.device,
                   batch_size: int = 16) -> dict:
    """Tiny start/end-position accuracy over sampled val rows (not QA EM/F1)."""
    model.eval()
    correct_s = correct_e = n = 0
    loader = DataLoader(WindowDataset(val_rows), batch_size=batch_size,
                        shuffle=False, collate_fn=lambda b: collate(b, pad_id))
    with torch.inference_mode():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"])
            pred_s = out.start_logits.argmax(dim=-1)
            pred_e = out.end_logits.argmax(dim=-1)
            mask = batch["start_positions"] >= 0
            correct_s += (pred_s[mask] == batch["start_positions"][mask]).sum().item()
            correct_e += (pred_e[mask] == batch["end_positions"][mask]).sum().item()
            n += int(mask.sum().item())
    model.train()
    return {"token_start_accuracy": correct_s / n if n else 0.0,
            "token_end_accuracy": correct_e / n if n else 0.0,
            "rows": n}


def save_checkpoint(model, tokenizer, out_dir: Path, meta: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    (out_dir / "training_meta.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8")


def train(args) -> int:
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer, get_linear_schedule_with_warmup

    device = get_device("cpu" if args.cpu else None)
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(args.seed)
    pin_memory = device.type == "cuda"

    print(f"[train] device={device} seed={args.seed}")
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    model = AutoModelForQuestionAnswering.from_pretrained(args.model).to(device)
    pad_id = tokenizer.pad_token_id

    print("[train] loading Phase 2 train features ...")
    t0 = time.perf_counter()
    all_rows = load_train_table(limit=args.read_limit)
    rows, sampling = sample_train_rows(
        all_rows, negative_ratio=args.negative_ratio,
        sample_limit=args.sample_limit, seed=args.seed)
    del all_rows
    print(f"[train] features ready in {time.perf_counter()-t0:.0f}s | "
          f"positives {sampling['positives_kept']}, negatives {sampling['negatives_kept']}, "
          f"total {sampling['total_rows']}")

    # small validation slice from the same sampled distribution (never test)
    rng = random.Random(args.seed + 1)
    val_rows = rng.sample(rows, min(args.val_rows, len(rows)))

    loader = DataLoader(
        WindowDataset(rows), batch_size=args.batch_size, shuffle=True,
        collate_fn=lambda b: collate(b, pad_id),
        num_workers=0, drop_last=False, pin_memory=pin_memory,
    )
    steps_per_epoch = math.ceil(len(loader) / args.grad_accum)
    total_steps = steps_per_epoch * args.epochs
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate,
                                  weight_decay=args.weight_decay)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(total_steps * args.warmup_ratio), total_steps)
    scaler = torch.amp.GradScaler(device.type, enabled=(device.type == "cuda" and args.amp))

    print(f"[train] {len(rows)} rows | {steps_per_epoch} steps/epoch | "
          f"{total_steps} total steps | batch {args.batch_size} x accum {args.grad_accum}")

    best_score = -1.0
    history = []
    global_step = 0
    t_start = time.perf_counter()
    model.train()
    stop = False
    for epoch in range(1, args.epochs + 1):
        if stop:
            break
        running = 0.0
        optimizer.zero_grad(set_to_none=True)
        for i, batch in enumerate(loader, 1):
            batch = {k: v.to(device, non_blocking=pin_memory) for k, v in batch.items()}
            with torch.autocast(device_type=device.type, dtype=torch.float16,
                                enabled=(device.type == "cuda" and args.amp)):
                out = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"],
                            start_positions=batch["start_positions"],
                            end_positions=batch["end_positions"])
                loss = out.loss / args.grad_accum
            scaler.scale(loss).backward()
            if i % args.grad_accum == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                global_step += 1
                running += out.loss.item()
                if global_step % args.log_every == 0:
                    print(f"[train] epoch {epoch} step {global_step}/{total_steps} "
                          f"loss {running / args.log_every:.4f} "
                          f"({time.perf_counter()-t_start:.0f}s)", flush=True)
                    running = 0.0
            if args.max_steps and global_step >= args.max_steps:
                stop = True
                print(f"[train] --max-steps {args.max_steps} reached; stopping")
                break
            if args.time_limit_min and (time.perf_counter() - t_start) > args.time_limit_min * 60:
                stop = True
                print(f"[train] --time-limit {args.time_limit_min}min reached; stopping")
                break

        metrics = evaluate_quick(model, val_rows, pad_id, device)
        metrics.update({"epoch": epoch, "global_step": global_step,
                        "wall_seconds": round(time.perf_counter() - t_start, 1)})
        history.append(metrics)
        print(f"[train] epoch {epoch} quick metrics: {metrics}")

        ckpt_dir = Path(args.checkpoints) / f"epoch{epoch}"
        save_checkpoint(model, tokenizer, ckpt_dir, {
            "args": vars(args), "sampling": sampling, "history": history,
            "device": device,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })
        score = metrics["token_start_accuracy"] + metrics["token_end_accuracy"]
        if score > best_score:
            best_score = score
            save_checkpoint(model, tokenizer, Path(args.output), {
                "args": vars(args), "sampling": sampling, "history": history,
                "device": device, "best": True,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            })
            print(f"[train] saved best model to {args.output}")

    print(f"[train] done in {time.perf_counter()-t_start:.0f}s | best score {best_score:.4f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="ContractIQ QA fine-tuning")
    ap.add_argument("--model", default=DEFAULT_BASELINE, help="HF model id or path")
    ap.add_argument("--train-dir", default=str(TRAIN_DIR))
    ap.add_argument("--output", default="ml/models/final")
    ap.add_argument("--checkpoints", default="ml/checkpoints")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--grad-accum", type=int, default=1)
    ap.add_argument("--learning-rate", "--lr", dest="learning_rate", type=float, default=3e-5)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--warmup-ratio", type=float, default=0.1)
    ap.add_argument("--max-grad-norm", type=float, default=1.0)
    ap.add_argument("--negative-ratio", type=float, default=3.0,
                    help="no-answer windows kept per positive window")
    ap.add_argument("--sample-limit", type=int, default=None,
                    help="cap on total training rows (after ratio sampling)")
    ap.add_argument("--read-limit", type=int, default=None,
                    help="cap on rows read from Parquet (RAM safety for tiny runs)")
    ap.add_argument("--val-rows", type=int, default=512)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--amp", action="store_true", help="mixed precision on CUDA")
    ap.add_argument("--cpu", action="store_true", help="force CPU even if CUDA exists")
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--time-limit-min", type=float, default=None)
    ap.add_argument("--log-every", type=int, default=25)
    ap.add_argument("--tiny", action="store_true",
                    help="local CPU proof run: small sample, 1 short pass, strict limits")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[2]
    args.output = str((root / args.output).resolve())
    args.checkpoints = str((root / args.checkpoints).resolve())
    if args.tiny:
        args.epochs = 1
        args.batch_size = 8
        args.sample_limit = args.sample_limit or 2048
        args.read_limit = args.read_limit or 120_000
        args.max_steps = args.max_steps or 120
        args.time_limit_min = args.time_limit_min or 15
        args.cpu = True
        args.output = str((root / "ml/models/tiny_cpu").resolve())
        args.checkpoints = str((root / "ml/checkpoints/tiny_cpu").resolve())
    return train(args)


if __name__ == "__main__":
    import sys

    sys.exit(main())
