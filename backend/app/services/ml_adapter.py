"""Adapter between the backend and the Phase 3 ML inference layer.

The backend depends ONLY on this interface (analyze_contract / model info),
never on MiniLM/transformers internals - so a future model swap (RoBERTa,
ONNX, another architecture) requires no backend changes. If no model can be
loaded, ModelUnavailable is raised; fake clause data is never generated.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol

from ..core.config import PROJECT_ROOT
from ..core.exceptions import ModelUnavailable


def _ensure_project_root_on_path() -> None:
    """Make the Phase 3 `ml` package importable regardless of the caller's cwd."""
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


class ClauseAnalyzer(Protocol):
    """Stable interface the backend codes against (Phase 3 ContractAnalyzer satisfies it)."""

    def analyze_contract(self, contract_text: str, enabled_clauses: list[str] | None = None) -> dict: ...
    def analyze_clause(self, contract_text: str, clause_label: str) -> dict: ...


class MLAnalyzerAdapter:
    """Lazy-loading wrapper around ml.src.inference.ContractAnalyzer."""

    def __init__(self, model_config_path: Path | None = None):
        self._model_config_path = model_config_path
        self._inner = None
        self._load_error: str | None = None

    @property
    def inner(self):
        if self._inner is None:
            if self._load_error is not None:
                raise ModelUnavailable(self._load_error)
            try:
                _ensure_project_root_on_path()
                from ml.src.inference import ContractAnalyzer

                kwargs = {}
                if self._model_config_path is not None:
                    kwargs["model_config_path"] = Path(self._model_config_path)
                self._inner = ContractAnalyzer(**kwargs)
            except Exception as exc:
                self._load_error = (
                    f"ML model could not be loaded: {type(exc).__name__}: {exc}"
                )
                raise ModelUnavailable(self._load_error) from exc
        return self._inner

    def analyze_contract(self, contract_text: str, enabled_clauses: list[str] | None = None) -> dict:
        return self.inner.analyze_contract(contract_text, enabled_clauses)

    def analyze_clause(self, contract_text: str, clause_label: str) -> dict:
        return self.inner.analyze_clause(contract_text, clause_label)

    @property
    def model_info(self) -> dict:
        return dict(self.inner.model_info)
