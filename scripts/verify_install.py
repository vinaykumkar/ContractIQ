#!/usr/bin/env python
"""Lightweight post-install verification (no model inference).

Checks: backend imports, config loading, database initialization, bundled
model files, device detection, parser/risk-engine imports. Exits 0/1.

Usage:  python scripts/verify_install.py     (called by setup_windows.bat)
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

failures: list[str] = []


def check(label: str, fn):
    try:
        fn()
        print(f"[OK]   {label}")
    except Exception as exc:
        failures.append(label)
        print(f"[FAIL] {label}: {type(exc).__name__}: {exc}")


def backend_imports():
    from app.main import create_app  # noqa: F401


def config_loads():
    from app.core.config import load_settings

    load_settings()


def db_initializes():
    from app.core.config import load_settings
    from app.db.database import get_engine, init_db

    engine = get_engine(load_settings().database_url)
    init_db(engine)
    engine.dispose()


def bundled_model_files():
    d = PROJECT_ROOT / "ml" / "models" / "final"
    for name in ("config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json"):
        if not (d / name).exists():
            raise FileNotFoundError(f"{name} missing from ml/models/final")


def device_detection():
    from ml.src.device import get_device

    get_device()


def retrieval_imports():
    import sklearn  # noqa: F401  (TF-IDF retrieval stage)


def parser_and_risk_imports():
    from app.risk.engine import evaluate_risk  # noqa: F401
    from app.services.document_parser import parse_document  # noqa: F401


check("Backend imports (FastAPI app)", backend_imports)
check("Configuration loads", config_loads)
check("Database initializes", db_initializes)
check("Bundled model files present", bundled_model_files)
check("Device detection (GPU/CPU auto)", device_detection)
check("Document parser + risk engine imports", parser_and_risk_imports)
check("Retrieval stage (scikit-learn) import", retrieval_imports)

print()
if failures:
    print(f"VERIFY INSTALL: FAILED ({len(failures)} problem(s)).")
    sys.exit(1)
print("VERIFY INSTALL: PASS — ContractIQ is ready. Run run_contractiq.bat to start.")
sys.exit(0)
