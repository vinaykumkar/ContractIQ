#!/usr/bin/env python
"""Verify the integrity of the immutable source archive.

The script checks whether data.zip still matches its recorded
SHA-256 checksum and expected file size.

Usage:
    python scripts/verify_data_integrity.py

Exit codes:
    0 = archive unchanged
    1 = archive missing or modified
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ARCHIVE_PATH = PROJECT_ROOT / "data.zip"

EXPECTED_SHA256 = (
    "f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a"
)

EXPECTED_SIZE = 18_309_308


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 digest of a file."""
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        while True:
            chunk = file.read(1 << 20)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def is_archive_valid(file_size: int, file_hash: str) -> bool:
    """Check the archive against the recorded integrity baseline."""
    return (
        file_size == EXPECTED_SIZE
        and file_hash == EXPECTED_SHA256
    )


def print_archive_details(file_size: int, file_hash: str) -> None:
    """Print the current archive integrity information."""
    print(
        f"data.zip size   : "
        f"{file_size:,} bytes "
        f"(expected {EXPECTED_SIZE:,})"
    )

    print(f"data.zip sha256 : {file_hash}")


def main() -> int:
    """Verify that the source archive has not changed."""
    if not ARCHIVE_PATH.is_file():
        print(
            "FAIL: data.zip is MISSING from the project root."
        )
        return 1

    current_size = ARCHIVE_PATH.stat().st_size
    current_hash = calculate_sha256(ARCHIVE_PATH)

    print_archive_details(
        current_size,
        current_hash,
    )

    if is_archive_valid(current_size, current_hash):
        print("OK: data.zip is unchanged.")
        return 0

    print(
        "FAIL: data.zip differs from the recorded baseline. "
        "DO NOT proceed."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
