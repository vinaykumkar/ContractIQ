#!/usr/bin/env python
"""Report the machine's ContractIQ readiness: versions, hardware, model, DB.

Prints a non-sensitive summary. No full analysis is run.

Usage:  python scripts/system_check.py
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

ok = True


def line(label: str, value: str, good: bool | None = None) -> None:
    global ok
    mark = "OK  " if good is True else ("WARN" if good is False else "INFO")
    if good is False:
        ok = False
    print(f"[{mark}] {label}: {value}")


line("Python", platform.python_version(), sys.version_info >= (3, 11) and sys.version_info < (3, 14))
line("OS", platform.platform())

try:
    import psutil

    line("RAM", f"{psutil.virtual_memory().total / 1e9:.1f} GB total")
except Exception:
    pass

try:
    import torch

    line("PyTorch", torch.__version__)
    cuda = torch.cuda.is_available()
    line("CUDA available", str(cuda), cuda)  # WARN (not fail) if absent - CPU works
    if cuda:
        props = torch.cuda.get_device_properties(0)
        line("GPU", f"{props.name} ({props.total_memory / 1e9:.1f} GB)")
        line("CUDA runtime", str(torch.version.cuda))
except Exception as exc:
    line("PyTorch", f"not importable ({type(exc).__name__})", False)

model = PROJECT_ROOT / "ml" / "models" / "final"
weights = model / "model.safetensors"
line("Bundled model dir", str(model.relative_to(PROJECT_ROOT)), model.exists())
line("Model weights", f"{weights.stat().st_size / 1e6:.0f} MB" if weights.exists() else "missing", weights.exists())
line("Tokenizer", "present" if (model / "tokenizer.json").exists() else "missing",
     (model / "tokenizer.json").exists())

db_default = PROJECT_ROOT / "storage" / "contractiq.db"
line("Database (default)", str(db_default.relative_to(PROJECT_ROOT)),
     db_default.exists() or True)  # created on first backend start

for req in ("backend/requirements.txt", "ml/requirements.txt", "frontend/package.json",
            "frontend/package-lock.json"):
    p = PROJECT_ROOT / req
    line(req, "present" if p.exists() else "MISSING", p.exists())

try:
    import subprocess

    node = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
    line("Node.js", node.stdout.strip() or "not found", node.returncode == 0)
except Exception:
    line("Node.js", "not found", False)

print()
print("System check:", "PASS" if ok else "ISSUES FOUND (see WARN/FAIL lines above)")
sys.exit(0 if ok else 1)
