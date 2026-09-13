#!/usr/bin/env python
"""Scan runtime source/config for machine-specific hard-coded paths.

Checks every runtime file for: the original project path, Windows user
folders, hard-coded Python/Node/venv paths, and absolute model/database
paths. Prints PASS or FAIL and exits 0/1.

Usage:  python scripts/check_portability.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = ["backend/app", "backend/tests", "ml/src", "ml/configs", "ml/tests",
             "scripts", "frontend/src", "docs", "reports"]
SCAN_SUFFIXES = {".py", ".ts", ".tsx", ".mjs", ".json", ".bat", ".md", ".example", ".html"}

BAD_PATTERNS = [
    (re.compile(r"c:\\\\proj2|c:/proj2|/c/proj2", re.I), "original project path C:\\proj2"),
    (re.compile(r"c:\\\\users\\|c:/users/", re.I), "Windows user folder C:\\Users\\"),
    (re.compile(r"vedant", re.I), "original username"),
    (re.compile(r"appdata\\\\local\\\\programs\\\\python|/appdata/local/programs/python", re.I), "hard-coded Python install path"),
    (re.compile(r"program files\\\\nodejs|program files/nodejs", re.I), "hard-coded Node install path"),
    (re.compile(r"\.venv\\\\|\.venv/", ), "hard-coded venv path (only allowed inside .bat via %PROJECT_DIR%)"),
    (re.compile(r"\\\\\\.cache\\\\huggingface|/\\.cache/huggingface", re.I), "hard-coded Hugging Face cache path"),
]


def runtime_files():
    for d in SCAN_DIRS:
        base = PROJECT_ROOT / d
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if (f.is_file() and f.suffix.lower() in SCAN_SUFFIXES
                and "node_modules" not in f.parts
                and f.resolve() != Path(__file__).resolve()):
                yield f
    for name in ("run_backend.bat", "run_frontend.bat", "run_contractiq.bat",
                 "setup_windows.bat", "stop_contractiq.bat", ".env.example"):
        f = PROJECT_ROOT / name
        if f.exists():
            yield f


def main() -> int:
    failures = []
    checked = 0
    for f in runtime_files():
        rel = f.relative_to(PROJECT_ROOT).as_posix()
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        checked += 1
        for pattern, label in BAD_PATTERNS:
            # .bat/.md files legitimately mention ".venv" (project-relative
            # activation and documentation prose) - not machine-specific paths
            if label.startswith("hard-coded venv") and f.suffix in (".bat", ".md"):
                continue
            m = pattern.search(content)
            if m:
                line_no = content[: m.start()].count("\n") + 1
                failures.append(f"{rel}:{line_no} -> {label}: {m.group(0)!r}")

    print(f"Checked {checked} runtime files for machine-specific paths.")
    if failures:
        print("FAIL — hard-coded paths found:")
        for f in failures:
            print(f"  {f}")
        return 1
    print("PASS — no machine-specific paths in runtime code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
