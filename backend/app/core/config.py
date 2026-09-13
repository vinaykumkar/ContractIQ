"""Central ContractIQ backend settings.

Every path is project-relative by default and overridable via environment
variables, so the project folder can be copied anywhere (e.g. D:\\Projects\\ContractIQ)
and still work. No absolute paths, usernames, or machine-specific values here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve(raw: str | Path) -> Path:
    """Resolve a possibly-relative path against the project root."""
    p = Path(raw)
    return p if p.is_absolute() else (PROJECT_ROOT / p)


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    """Runtime settings with safe defaults; all overridable via env vars."""

    # database (default: project-relative SQLite file)
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "CONTRACTIQ_DB_URL", f"sqlite:///{_resolve('storage/contractiq.db')}"
        )
    )
    # storage directories (project-relative by default)
    upload_dir: Path = field(
        default_factory=lambda: _resolve(os.environ.get("CONTRACTIQ_UPLOAD_DIR", "storage/uploads"))
    )
    temp_dir: Path = field(
        default_factory=lambda: _resolve(os.environ.get("CONTRACTIQ_TEMP_DIR", "storage/temp"))
    )
    # upload policy
    max_upload_mb: int = field(default_factory=lambda: _env_int("CONTRACTIQ_MAX_UPLOAD_MB", 20))
    allowed_extensions: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})
    # raw text retention: full contract text is stored ONLY when this is on
    # (the UI evidence-highlighting feature needs it; documented in SECURITY.md)
    store_raw_text: bool = field(default_factory=lambda: _env_bool("CONTRACTIQ_STORE_RAW_TEXT", True))
    upload_retention_hours: int = field(
        default_factory=lambda: _env_int("CONTRACTIQ_UPLOAD_RETENTION_HOURS", 24)
    )
    # ML layer
    ml_model_config: Path = field(
        default_factory=lambda: _resolve(os.environ.get("CONTRACTIQ_ML_MODEL_CONFIG", "ml/configs/model.json"))
    )
    # risk engine
    risk_min_confidence: float = field(
        default_factory=lambda: float(os.environ.get("CONTRACTIQ_RISK_MIN_CONFIDENCE", "0.5"))
    )
    risk_bands_path: Path = field(
        default_factory=lambda: _resolve("ml/configs/clauses.json")
    )
    # API (Phase 5)
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.environ.get(
            "CONTRACTIQ_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if o.strip()
    ])

    def ensure_storage_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """Build settings from the environment (cheap; call per request scope)."""
    return Settings()


def risk_bands(settings: Settings | None = None) -> dict:
    """Risk bands from the central clause registry, with safe fallbacks."""
    bands = {"low_max": 30, "medium_max": 60}
    path = (settings or load_settings()).risk_bands_path
    try:
        registry = json_loads(path.read_text(encoding="utf-8"))
        rb = registry.get("risk_bands", {})
        if "low_max" in rb:
            bands["low_max"] = int(rb["low_max"])
        if "medium_max" in rb:
            bands["medium_max"] = int(rb["medium_max"])
    except Exception:
        pass  # fallback bands remain valid
    return bands


def json_loads(text: str) -> dict:
    import json

    return json.loads(text)
