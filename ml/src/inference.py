"""ContractIQ ML inference service.

Public interface (used by Phase 5 backend and the evaluation framework):

    analyzer = ContractAnalyzer()
    result   = analyzer.analyze_contract(contract_text)          # full dict
    for clause_result in analyzer.analyze_contract_iter(text):   # streaming
        ...
    one       = analyzer.analyze_clause(text, "governing_law")

Model resolution (never silently pretends):
  1. ml/models/final/ exists (fine-tuned checkpoint)  -> state "fine_tuned"
  2. otherwise the configured baseline from the HF Hub -> state "zero_shot_baseline"
  3. if neither can be loaded, a clear InferenceError is raised.

Every clause result reports found / text / confidence / exact character
offsets into the original contract text (text is always an exact substring).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import torch

from .chunking import (
    TokenizedContext,
    build_windows_for_token_slice,
    tokenize_context,
    validate_window_fit,
)
from .config import (
    ML_CONFIG_DIR,
    PROJECT_ROOT,
    load_enabled_clauses,
    load_window_config,
)
from .decoder import ClauseDecision, WindowPrediction, decode_window, decision_to_dict
from .device import device_summary, get_device
from .retrieval import merge_regions, select_regions

MODEL_CONFIG_PATH = ML_CONFIG_DIR / "model.json"
FINAL_MODEL_DIR = PROJECT_ROOT / "ml" / "models" / "final"


class InferenceError(RuntimeError):
    """Raised when no usable QA model can be loaded."""


def load_model_config(path: Path = MODEL_CONFIG_PATH) -> dict:
    if not path.exists():
        raise InferenceError(
            f"Model config not found at {path}. The ML layer is not set up."
        )
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class RawClausePrediction:
    """Best span across all windows of one clause, before threshold decision."""

    span_confidence: float
    cls_confidence: float
    start_char: int
    end_char: int
    windows_considered: int


class ContractAnalyzer:
    """QA-based clause extraction over contracts (CPU-first design)."""

    def __init__(
        self,
        model_config_path: Path = MODEL_CONFIG_PATH,
        device: str | None = None,
        quiet: bool = False,
    ):
        self.config = load_model_config(model_config_path)
        self.window_cfg = load_window_config()
        self._load_clause_registry()
        self.device = get_device(device)
        if not torch.cuda.is_available():
            # A CUDA-build torch whose driver can't run it segfaults when transformers
            # probes CUDA stream-capture state during attention-mask creation; on a
            # CPU-only run that probe is always False, so replace it with a safe stub.
            torch.cuda.is_current_stream_capturing = lambda *a, **k: False
        self.quiet = quiet
        self._tokenizer, self._model, self.model_info = self._resolve_model()
        torch.set_num_threads(int(self.config.get("performance", {}).get("torch_threads", 8)))
        self._question_cache: dict[str, list[int]] = {}
        self._tokenized_cache: dict[str, TokenizedContext] = {}
        self._log(f"device: {device_summary(self.device)}")

    # ---------------------------------------------------------- model loading

    def _load_clause_registry(self):
        from .config import ConfigError

        try:
            self.clauses = {c.label: c for c in load_enabled_clauses()}
        except ConfigError as exc:
            raise InferenceError(str(exc)) from exc

    def _resolve_model(self):
        from transformers import AutoModelForQuestionAnswering, AutoTokenizer

        final_dir = PROJECT_ROOT / self.config.get("final_model", {}).get("path", "ml/models/final")
        baseline_id = self.config["baseline_model"]["model_id"]
        version = self.config.get("model_version", "unknown")

        # CUDA-build torch on a machine whose driver can't run it segfaults in the
        # SDPA attention path (it probes CUDA stream state); use eager attention there.
        import torch as _torch
        attn = "sdpa" if _torch.cuda.is_available() else "eager"

        if (final_dir / "config.json").exists():
            try:
                tok = AutoTokenizer.from_pretrained(str(final_dir), use_fast=True)
                model = AutoModelForQuestionAnswering.from_pretrained(
                    str(final_dir), attn_implementation=attn)
                model.to(self.device)
                info = {
                    "state": "fine_tuned",
                    "source": str(final_dir.relative_to(PROJECT_ROOT)),
                    "model_version": version,
                }
                self._log(f"Loaded FINE-TUNED model from {final_dir}")
                return tok, model, info
            except Exception as exc:
                self._log(f"[warn] final model at {final_dir} failed to load ({exc}); "
                          "falling back to baseline")

        try:
            tok = AutoTokenizer.from_pretrained(baseline_id, use_fast=True)
            model = AutoModelForQuestionAnswering.from_pretrained(
                baseline_id, attn_implementation=attn)
            model.to(self.device)
        except Exception as exc:
            raise InferenceError(
                f"Could not load the baseline QA model '{baseline_id}' ({exc}). "
                "Download it once (internet needed on first run) or place a "
                "fine-tuned checkpoint in ml/models/final/."
            ) from exc
        info = {
            "state": "zero_shot_baseline",
            "source": baseline_id,
            "model_version": version,
        }
        self._log("Loaded ZERO-SHOT BASELINE model "
                  f"({baseline_id}) - not fine-tuned on CUAD")
        return tok, model, info

    def _log(self, msg: str) -> None:
        if not self.quiet:
            print(f"[ContractAnalyzer] {msg}")

    # ------------------------------------------------------------ internals

    def _question_ids(self, label: str) -> list[int]:
        if label not in self._question_cache:
            clause = self.clauses.get(label)
            if clause is None:
                raise KeyError(f"Unknown clause label '{label}'. "
                               f"Enabled: {sorted(self.clauses)}")
            validate_window_fit(self.window_cfg, self._tokenizer, clause.question, label)
            self._question_cache[label] = self._tokenizer(
                clause.question, add_special_tokens=False
            )["input_ids"]
        return self._question_cache[label]

    def _tokenized(self, contract_text: str, contract_id: str = "document") -> TokenizedContext:
        key = f"{contract_id}:{hash(contract_text) & 0xFFFFFFFF}"
        if key not in self._tokenized_cache:
            self._tokenized_cache = {key: tokenize_context(self._tokenizer, _Shim(contract_id, contract_text))}
        return self._tokenized_cache[key]

    def _windows_for_clause(self, tokenized: TokenizedContext, label: str) -> tuple[list, list]:
        """Windows for one clause, honouring the per-clause retrieval strategy."""
        q_ids = self._question_ids(label)
        retrieval = self.config.get("retrieval", {})
        clause = self.clauses[label]
        full_doc_labels = set(retrieval.get("full_document_clauses", []))

        if retrieval.get("enabled") and label not in full_doc_labels:
            regions = select_regions(
                tokenized.context, clause,
                top_k=int(retrieval.get("top_k", 15)),
                max_block_chars=int(retrieval.get("max_block_chars", 1200)),
                overlap_chars=int(retrieval.get("overlap_chars", 200)),
                boost_first_blocks=int(retrieval.get("boost_first_blocks", 2)),
            )
            ranges = merge_regions(regions)
        else:
            ranges = [(0, len(tokenized.context))]

        # char ranges -> token ranges in the (single) tokenized context
        offsets = tokenized.offsets
        windows = []
        for r_start, r_end in ranges:
            # tokens intersecting the char range
            lo, hi = 0, len(offsets)
            while lo < hi and offsets[lo][1] <= r_start:
                lo += 1
            while hi > lo and offsets[hi - 1][0] >= r_end:
                hi -= 1
            if hi <= lo:
                continue
            windows.extend(build_windows_for_token_slice(
                tokenized, lo, hi, q_ids, label, self.window_cfg,
                self._tokenizer.cls_token_id, self._tokenizer.sep_token_id,
                first_window_index=len(windows),
            ))
        return windows, ranges

    def _forward(self, windows: list) -> list[WindowPrediction]:
        """Batched forward + per-window span decoding (bounded batch size)."""
        batch_size = int(self.config.get("performance", {}).get("batch_size", 8))
        max_ans = int(self.config["windowing"]["max_answer_tokens"])
        pad_id = self._tokenizer.pad_token_id
        preds: list[WindowPrediction] = []
        with torch.inference_mode():
            for i in range(0, len(windows), batch_size):
                chunk = windows[i : i + batch_size]
                max_len = max(len(w.input_ids) for w in chunk)
                input_ids = torch.tensor(
                    [w.input_ids + [pad_id] * (max_len - len(w.input_ids)) for w in chunk],
                    dtype=torch.long, device=self.device,
                )
                attention = torch.tensor(
                    [[1] * len(w.input_ids) + [0] * (max_len - len(w.input_ids)) for w in chunk],
                    dtype=torch.long, device=self.device,
                )
                out = self._model(input_ids=input_ids, attention_mask=attention)
                for k, w in enumerate(chunk):
                    ctx_from = w.ctx_first_token_index_in_window
                    ctx_to = ctx_from + (w.ctx_token_end - w.ctx_token_start)
                    preds.append(decode_window(
                        out.start_logits[k], out.end_logits[k],
                        ctx_from, ctx_to, max_ans, window_index=w.window_index,
                    ))
        return preds

    def _raw_prediction(self, contract_text: str, label: str,
                        tokenized: TokenizedContext | None = None) -> tuple[RawClausePrediction, dict]:
        tokenized = tokenized or self._tokenized(contract_text)
        t0 = time.perf_counter()
        windows, ranges = self._windows_for_clause(tokenized, label)
        if not windows:
            return (RawClausePrediction(0.0, 0.0, -1, -1, 0),
                    {"windows": 0, "processing_ms": 0.0, "ranges": []})
        preds = self._forward(windows)
        best_span = max(preds, key=lambda p: p.span_confidence)
        cls_score = max(p.cls_confidence for p in preds)
        # map winning token indexes back to original char offsets
        win = next(w for w in windows if w.window_index == best_span.window_index)
        local_s = best_span.start_token - win.ctx_first_token_index_in_window
        local_e = best_span.end_token - win.ctx_first_token_index_in_window
        start_char = win.ctx_offsets[local_s][0]
        end_char = win.ctx_offsets[local_e][1]
        ms = (time.perf_counter() - t0) * 1000
        return (
            RawClausePrediction(
                span_confidence=round(best_span.span_confidence, 6),
                cls_confidence=round(cls_score, 6),
                start_char=start_char,
                end_char=end_char,
                windows_considered=len(windows),
            ),
            {"windows": len(windows), "processing_ms": round(ms, 1), "ranges": ranges},
        )

    def _decide(self, label: str, raw: RawClausePrediction, context: str) -> ClauseDecision:
        dec = self.config["decoding"]
        found = (
            raw.span_confidence >= float(dec.get("min_confidence", 0.0))
            and (raw.span_confidence - raw.cls_confidence) >= float(dec.get("no_answer_delta", 0.0))
        )
        if found and raw.start_char >= 0:
            text = context[raw.start_char:raw.end_char]
        else:
            text = ""
        return ClauseDecision(
            clause_label=label, found=bool(found), text=text,
            confidence=raw.span_confidence,
            start_char=raw.start_char if found else -1,
            end_char=raw.end_char if found else -1,
            no_answer_score=raw.cls_confidence,
            window_index=None, windows_considered=raw.windows_considered,
        )

    # ---------------------------------------------------------- public API

    def analyze_clause(self, contract_text: str, clause_label: str) -> dict:
        """Analyze one clause of one contract. Returns the public result dict."""
        tokenized = self._tokenized(contract_text)
        raw, meta = self._raw_prediction(contract_text, clause_label, tokenized)
        decision = self._decide(clause_label, raw, tokenized.context)
        out = decision_to_dict(decision)
        out.update({
            "question": self.clauses[clause_label].question,
            "model_state": self.model_info["state"],
            "model_version": self.model_info["model_version"],
            "processing_ms": meta["processing_ms"],
        })
        return out

    def iter_raw(self, contract_text: str, enabled_clauses: list[str] | None = None):
        """Yield (label, RawClausePrediction, meta) per clause without thresholds.

        Used by calibration/evaluation so threshold sweeps never re-run the model.
        """
        labels = enabled_clauses or list(self.clauses)
        tokenized = self._tokenized(contract_text)
        for label in labels:
            raw, meta = self._raw_prediction(contract_text, label, tokenized)
            yield label, raw, meta

    def analyze_contract_iter(self, contract_text: str, enabled_clauses: list[str] | None = None):
        """Yield per-clause result dicts as soon as each clause completes.

        This is the hook the Phase 5 backend will use for progressive updates.
        The contract text is tokenized exactly once and shared across clauses.
        """
        labels = enabled_clauses or list(self.clauses)
        tokenized = self._tokenized(contract_text)
        t0 = time.perf_counter()
        for label in labels:
            raw, meta = self._raw_prediction(contract_text, label, tokenized)
            decision = self._decide(label, raw, tokenized.context)
            out = decision_to_dict(decision)
            out.update({
                "question": self.clauses[label].question,
                "model_state": self.model_info["state"],
                "model_version": self.model_info["model_version"],
                "processing_ms": meta["processing_ms"],
            })
            yield out
        total_ms = (time.perf_counter() - t0) * 1000
        yield {"_summary": {
            "total_processing_ms": round(total_ms, 1),
            "clauses": len(labels),
            "model_state": self.model_info["state"],
            "model_version": self.model_info["model_version"],
        }}

    def analyze_contract(self, contract_text: str, enabled_clauses: list[str] | None = None) -> dict:
        """Analyze all enabled clauses; returns the full structured result."""
        results = []
        summary = {}
        for item in self.analyze_contract_iter(contract_text, enabled_clauses):
            if "_summary" in item:
                summary = item["_summary"]
            else:
                results.append(item)
        return {
            "clauses": results,
            "model_state": summary.get("model_state", self.model_info["state"]),
            "model_version": summary.get("model_version", self.model_info["model_version"]),
            "total_processing_ms": summary.get("total_processing_ms"),
            "disclaimer": "AI-assisted analysis. Results should be reviewed by a qualified professional.",
        }


class _Shim:
    """Minimal object satisfying tokenize_context's record interface."""

    def __init__(self, contract_id: str, context: str):
        self.contract_id = contract_id
        self.context = context
