#!/usr/bin/env python
"""Verify that the immutable source archive data.zip has not changed.

Usage:
    python scripts/verify_data_integrity.py

Exit code 0 = unchanged, 1 = MODIFIED (investigate immediately).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = PROJECT_ROOT / "data.zip"
EXPECTED_SHA256 = "f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a"
EXPECTED_SIZE = 18309308


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not ZIP_PATH.exists():
        print("FAIL: data.zip is MISSING from the project root.")
        return 1
    size = ZIP_PATH.stat().st_size
    digest = sha256_of(ZIP_PATH)
    print(f"data.zip size   : {size:,} bytes (expected {EXPECTED_SIZE:,})")
    print(f"data.zip sha256 : {digest}")
    if size == EXPECTED_SIZE and digest == EXPECTED_SHA256:
        print("OK: data.zip is unchanged.")
        return 0
    print("FAIL: data.zip differs from the recorded baseline. DO NOT proceed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
