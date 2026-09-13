"""Central configuration for the ContractIQ ML pipeline.

All paths resolve relative to the project root (never hard-coded), and the
single source of truth for clauses/windowing is ml/configs/clauses.json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_CONFIG_DIR = PROJECT_ROOT / "ml" / "configs"
CLAUSE_REGISTRY_PATH = ML_CONFIG_DIR / "clauses.json"

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

CUADV1_PATH = RAW_DIR / "CUADv1.json"
TRAIN_SEPARATE_PATH = RAW_DIR / "train_separate_questions.json"
TEST_PATH = RAW_DIR / "test.json"

REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_TOKENIZER_NAME = "distilbert-base-uncased"
DEFAULT_SEED = 42
DEFAULT_VAL_FRACTION = 0.10


class ConfigError(RuntimeError):
    """Raised when the central configuration is missing or inconsistent."""


@dataclass(frozen=True)
class ClauseSpec:
    """One clause as registered in ml/configs/clauses.json."""

    label: str
    cuad_category: str
    question: str
    enabled: bool


@dataclass(frozen=True)
class WindowConfig:
    """Sliding-window parameters (shared by training and inference)."""

    max_seq_len: int
    doc_stride: int
    max_answer_tokens: int
    no_answer_threshold: float
    min_confidence: float

    def __post_init__(self) -> None:
        if not 32 <= self.max_seq_len <= 2048:
            raise ConfigError(f"max_seq_len out of range: {self.max_seq_len}")
        if not 0 < self.doc_stride < self.max_seq_len - 16:
            raise ConfigError(
                f"doc_stride must be in (0, max_seq_len-16); got {self.doc_stride}"
            )
        if not 0 <= self.no_answer_threshold <= 1:
            raise ConfigError(f"no_answer_threshold must be in [0, 1]")

    def check_tokenizer_compat(self, model_max_length: int) -> None:
        """Fail loudly if the configured window exceeds the tokenizer/model limit."""
        if model_max_length is None or model_max_length <= 0:
            # Some tokenizers report 1e30 meaning "no limit" - treat as compatible.
            return
        if self.max_seq_len > model_max_length:
            raise ConfigError(
                f"max_seq_len={self.max_seq_len} exceeds tokenizer model_max_length="
                f"{model_max_length}; lower max_seq_len in ml/configs/clauses.json"
            )


@dataclass(frozen=True)
class EnabledClause(ClauseSpec):
    """A clause enabled for Version 1 (label is always set)."""


def load_clause_registry(path: Path = CLAUSE_REGISTRY_PATH) -> tuple[list[ClauseSpec], dict]:
    """Load the central clause registry.

    Returns (all_clauses, full_registry_dict) where full_registry_dict includes
    the inference/window and risk-band blocks.
    """
    if not path.exists():
        raise ConfigError(
            f"Clause registry not found at {path}. "
            "Regenerate it with: python scripts/generate_clause_config.py"
        )
    registry = json.loads(path.read_text(encoding="utf-8"))
    clauses = [
        ClauseSpec(
            label=c.get("label", ""),
            cuad_category=c["cuad_category"],
            question=c["question"],
            enabled=bool(c.get("enabled", False)),
        )
        for c in registry.get("clauses", [])
    ]
    if not clauses:
        raise ConfigError("Clause registry contains no clauses.")
    labels = [c.label for c in clauses if c.enabled]
    if len(set(labels)) != len(labels):
        raise ConfigError("Duplicate labels among enabled clauses.")
    for c in clauses:
        if c.enabled and not c.label:
            raise ConfigError(f"Enabled clause '{c.cuad_category}' has no label.")
    return clauses, registry


def load_enabled_clauses(path: Path = CLAUSE_REGISTRY_PATH) -> list[EnabledClause]:
    """Return only the enabled clauses, in registry order."""
    clauses, _ = load_clause_registry(path)
    return [EnabledClause(c.label, c.cuad_category, c.question, True) for c in clauses if c.enabled]


def load_window_config(path: Path = CLAUSE_REGISTRY_PATH) -> WindowConfig:
    """Load windowing/QA parameters from the central registry's inference block."""
    _, registry = load_clause_registry(path)
    inf = registry.get("inference", {})
    try:
        return WindowConfig(
            max_seq_len=int(inf["max_seq_len"]),
            doc_stride=int(inf["doc_stride"]),
            max_answer_tokens=int(inf["max_answer_tokens"]),
            no_answer_threshold=float(inf["no_answer_threshold"]),
            min_confidence=float(inf["min_confidence"]),
        )
    except KeyError as exc:
        raise ConfigError(f"Missing inference config key in {path}: {exc}") from exc
