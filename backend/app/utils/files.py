"""File-safety utilities: filename sanitization, upload validation, storage.

Uploads are untrusted input. Filenames are never used as storage paths
(generated UUID ids are), path traversal is rejected, and file content is
never executed — only parsed as data.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from ..core.config import Settings, load_settings
from ..core.exceptions import (
    EmptyFileError,
    FileTooLarge,
    InvalidFilename,
    UnsupportedFileType,
)

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._ -]+")
_TRAVERSAL_HINT = re.compile(r"(\.\.[\\/])|([\\/])|(^\.+$)")


def sanitize_filename(filename: str, max_length: int = 150) -> str:
    """Return a safe display filename; raise InvalidFilename when hopeless.

    - strips any directory components (defends path traversal)
    - replaces unsafe characters
    - rejects names that are empty after cleaning
    The result is used only for display/traceability, never as a storage path.
    """
    if not filename or not filename.strip():
        raise InvalidFilename("Filename is empty.")
    name = Path(filename).name  # drop any folder components
    if _TRAVERSAL_HINT.search(name):
        name = name.replace("\\", "/").split("/")[-1] or "upload"
    cleaned = _UNSAFE_CHARS.sub("_", name).strip(" ._")
    if not cleaned or set(cleaned) <= {"."}:
        raise InvalidFilename("Filename contains no usable characters.")
    return cleaned[:max_length]


def validate_upload(filename: str, size_bytes: int, settings: Settings | None = None) -> str:
    """Validate extension + size; returns the sanitized display filename."""
    s = settings or load_settings()
    safe_name = sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in s.allowed_extensions:
        raise UnsupportedFileType(
            f"File type '{ext or '(none)'}' is not supported. "
            f"Allowed: {', '.join(sorted(s.allowed_extensions))}."
        )
    if size_bytes <= 0:
        raise EmptyFileError()
    max_bytes = s.max_upload_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise FileTooLarge(f"File is {size_bytes} bytes; limit is {max_bytes}.")
    return safe_name


def stored_file_path(upload_dir: Path, internal_id: str, extension: str) -> Path:
    """Path for a stored upload: <upload_dir>/<uuid><ext> (never user-controlled)."""
    ext = extension.lower() if extension.startswith(".") else f".{extension}"
    return (upload_dir / f"{internal_id}{ext}").resolve()


def save_upload(content: bytes, original_filename: str, settings: Settings | None = None) -> tuple[Path, str, str]:
    """Validate and persist an upload under a generated internal id.

    Returns (stored_path, internal_id, sanitized_display_name).
    """
    s = settings or load_settings()
    safe_name = validate_upload(original_filename, len(content), s)
    s.ensure_storage_dirs()
    internal_id = uuid.uuid4().hex
    ext = Path(safe_name).suffix.lower()
    path = stored_file_path(s.upload_dir, internal_id, ext)
    # containment check: the resolved path must stay inside upload_dir
    if not str(path).startswith(str(s.upload_dir.resolve())):
        raise InvalidFilename("Resolved storage path escaped the upload directory.")
    path.write_bytes(content)
    return path, internal_id, safe_name


def delete_stored_file(path: Path) -> bool:
    """Best-effort removal of a stored file; returns True when deleted."""
    try:
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except OSError:
        return False
    return False


def cleanup_temp_files(max_age_hours: int, settings: Settings | None = None) -> int:
    """Remove temp files older than max_age_hours; returns deleted count."""
    import time

    s = settings or load_settings()
    s.temp_dir.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for f in s.temp_dir.iterdir():
        try:
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    return removed
