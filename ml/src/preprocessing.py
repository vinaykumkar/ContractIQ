"""Contract-level splitting, leakage checks, and streaming feature preparation.

Split policy (documented decision):
- The official test set (test.json) is NEVER touched for tuning or splitting.
- A validation split is carved ONLY from the 408 official training contracts,
  at CONTRACT level (all QAs of a contract stay together - no leakage).
- The split is deterministic (seeded shuffle of sorted contract ids).

Training feature policy (documented decision):
- One window set per (contract, clause). Each window is labeled with the FIRST
  gold span (document order) it fully contains, or [CLS] when the window
  contains no full span. This follows standard SQuAD practice and avoids the
  conflicting-label duplication the exploded Category_N file would introduce
  (identical window text appearing with different targets).
- Every gold span that falls inside at least one window still receives
  supervision, and windows outside any span train the no-answer/CLS head.

Features are streamed contract-by-contract and sharded to Parquet under
data/processed/ - full tokenized windows are never materialized in RAM.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .chunking import (
    TokenizedContext,
    build_windows_for_clause,
    tokenize_context,
    validate_window_fit,
)
from .config import PROCESSED_DIR, ClauseSpec, WindowConfig
from .cuad_loader import ContractRecord
from .qa_features import answer_token_positions, build_eval_features, cls_index

TRAIN = "train"
VAL = "val"
TEST = "test"


# ---------------------------------------------------------------- splitting

@dataclass
class SplitInfo:
    seed: int
    val_fraction: float
    train_ids: list[str]
    val_ids: list[str]

    @property
    def counts(self) -> dict:
        return {"train": len(self.train_ids), "val": len(self.val_ids)}


def assign_splits(
    records: list[ContractRecord], seed: int = 42, val_fraction: float = 0.10
) -> SplitInfo:
    """Deterministically split contracts into train/val (contract level)."""
    ids = sorted(r.contract_id for r in records)
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate contract ids - cannot split safely.")
    rng = random.Random(seed)
    rng.shuffle(ids)
    n_val = max(1, round(len(ids) * val_fraction))
    val_ids = set(ids[:n_val])
    for r in records:
        r.split = VAL if r.contract_id in val_ids else TRAIN
    return SplitInfo(
        seed=seed,
        val_fraction=val_fraction,
        train_ids=sorted(i for i in ids if i not in val_ids),
        val_ids=sorted(val_ids),
    )


def save_split_metadata(info: SplitInfo, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "seed": info.seed,
                "val_fraction": info.val_fraction,
                "split_at": "contract level",
                "source": "train_separate_questions.json only (official test set untouched)",
                "counts": info.counts,
                "train_ids": info.train_ids,
                "val_ids": info.val_ids,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def leakage_report(
    train_ids: list[str], val_ids: list[str], test_ids: list[str]
) -> dict:
    train_set, val_set, test_set = set(train_ids), set(val_ids), set(test_ids)
    return {
        "train_overlap_val": sorted(train_set & val_set),
        "train_overlap_test": sorted(train_set & test_set),
        "val_overlap_test": sorted(val_set & test_set),
        "duplicates_within_train": len(train_ids) - len(train_set),
        "duplicates_within_val": len(val_ids) - len(val_set),
        "duplicates_within_test": len(test_ids) - len(test_set),
        "counts": {
            "train": len(train_set),
            "val": len(val_set),
            "test": len(test_set),
        },
    }


# ------------------------------------------------------------ question budget

def question_budget(clauses: list[ClauseSpec], config: WindowConfig, tokenizer) -> list[dict]:
    """Per enabled clause: question token length and remaining context budget."""
    report = []
    for c in clauses:
        if not c.enabled:
            continue
        q_len = validate_window_fit(config, tokenizer, c.question, c.label)
        report.append(
            {
                "label": c.label,
                "cuad_category": c.cuad_category,
                "question_tokens": q_len,
                "special_tokens": 3,
                "context_budget": config.max_seq_len - q_len - 3,
                "at_risk": False,
            }
        )
    return report


# --------------------------------------------------------- feature preparation

def _gold_spans_in_file_order(record: ContractRecord, clause_label: str):
    spans = []
    for qa in record.qas:
        if qa.clause_label == clause_label and not qa.is_impossible and qa.answers:
            spans.append(qa.answers[0])
    return spans


def iter_contract_features(
    record: ContractRecord,
    clauses: list[ClauseSpec],
    config: WindowConfig,
    tokenizer,
    cls_token_id: int,
    sep_token_id: int,
    split: str,
    tokenized_cache: dict[str, TokenizedContext] | None = None,
):
    """Yield one feature dict per (contract, clause, window).

    split="train": rows carry start/end positions (CLS-based no-answer).
    split="val": rows carry eval metadata (context char offsets) only.
    """
    tokenized = tokenize_context(tokenizer, record)
    if tokenized_cache is not None:
        tokenized_cache[record.contract_id] = tokenized
    for clause in clauses:
        if not clause.enabled:
            continue
        q_ids = tokenizer(clause.question, add_special_tokens=False)["input_ids"]
        windows = build_windows_for_clause(
            tokenized, q_ids, clause.label, config, cls_token_id, sep_token_id
        )
        if split == TRAIN:
            gold_spans = _gold_spans_in_file_order(record, clause.label)
            has_gold = bool(gold_spans)
            for w in windows:
                span_pos = None
                span_chars = None
                source_qa = ""
                for qa in record.qas:
                    if qa.clause_label != clause.label or qa.is_impossible or not qa.answers:
                        continue
                    pos = answer_token_positions(w, qa.answers[0])
                    if pos is not None:
                        span_pos = pos
                        span_chars = (qa.answers[0].start, qa.answers[0].end)
                        source_qa = qa.qa_id
                        break
                if source_qa == "" and record.qas:
                    source_qa = next(
                        (qa.qa_id for qa in record.qas if qa.clause_label == clause.label), ""
                    )
                no_answer = span_pos is None
                yield {
                    "input_ids": w.input_ids,
                    "start_position": cls_index() if no_answer else span_pos[0],
                    "end_position": cls_index() if no_answer else span_pos[1],
                    "contract_id": w.contract_id,
                    "clause_label": w.clause_label,
                    "qa_id": source_qa,
                    "window_index": w.window_index,
                    "is_no_answer": no_answer,
                    "gold_char_start": None if span_chars is None else span_chars[0],
                    "gold_char_end": None if span_chars is None else span_chars[1],
                }
        else:
            is_no_answer_example = not _gold_spans_in_file_order(record, clause.label)
            qa_id = next(
                (qa.qa_id for qa in record.qas if qa.clause_label == clause.label), ""
            )
            for feats in build_eval_features(windows, qa_dummy(qa_id, clause.label, is_no_answer_example)):
                yield {
                    "input_ids": feats.input_ids,
                    "contract_id": feats.contract_id,
                    "clause_label": feats.clause_label,
                    "qa_id": feats.qa_id,
                    "window_index": feats.window_index,
                    "is_no_answer_example": feats.is_no_answer_example,
                    "offset_start": [o[0] for o in feats.ctx_offsets],
                    "offset_end": [o[1] for o in feats.ctx_offsets],
                }


def qa_dummy(qa_id: str, clause_label: str, is_impossible: bool):
    """Tiny helper mirroring the qa fields build_eval_features reads."""
    from .cuad_loader import ClauseQA

    return ClauseQA(clause_label=clause_label, cuad_category="", question="",
                    answers=[], is_impossible=is_impossible, qa_id=qa_id)


TRAIN_SCHEMA = pa.schema(
    [
        ("input_ids", pa.list_(pa.int32())),
        ("start_position", pa.int32()),
        ("end_position", pa.int32()),
        ("contract_id", pa.string()),
        ("clause_label", pa.string()),
        ("qa_id", pa.string()),
        ("window_index", pa.int32()),
        ("is_no_answer", pa.bool_()),
        ("gold_char_start", pa.int32()),
        ("gold_char_end", pa.int32()),
    ]
)

EVAL_SCHEMA = pa.schema(
    [
        ("input_ids", pa.list_(pa.int32())),
        ("contract_id", pa.string()),
        ("clause_label", pa.string()),
        ("qa_id", pa.string()),
        ("window_index", pa.int32()),
        ("is_no_answer_example", pa.bool_()),
        ("offset_start", pa.list_(pa.int32())),
        ("offset_end", pa.list_(pa.int32())),
    ]
)


class FeatureWriter:
    """Shard feature dicts to Parquet under data/processed/ with bounded RAM.

    A handful of large shards keeps the file count sane; the format is directly
    readable by Hugging Face datasets / pyarrow / pandas.
    """

    def __init__(self, out_dir: Path, schema: pa.Schema, shard_rows: int = 50_000):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.schema = schema
        self.shard_rows = shard_rows
        self.buffer: list[dict] = []
        self.files: list[str] = []
        self.rows_written = 0

    def add(self, row: dict) -> None:
        self.buffer.append(row)
        if len(self.buffer) >= self.shard_rows:
            self._flush()

    def _flush(self) -> None:
        if not self.buffer:
            return
        table = pa.Table.from_pylist(self.buffer, schema=self.schema)
        shard = self.out_dir / f"shard_{len(self.files):05d}.parquet"
        pq.write_table(table, shard)
        self.files.append(str(shard))
        self.rows_written += len(self.buffer)
        self.buffer = []

    def close(self) -> tuple[list[str], int]:
        self._flush()
        return self.files, self.rows_written
