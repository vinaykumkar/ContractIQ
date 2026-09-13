"""File-safety utility tests: sanitization, traversal, validation, storage."""
from __future__ import annotations

import pytest

from app.core.exceptions import (
    EmptyFileError,
    FileTooLarge,
    InvalidFilename,
    UnsupportedFileType,
)
from app.utils.files import (
    cleanup_temp_files,
    delete_stored_file,
    sanitize_filename,
    save_upload,
    validate_upload,
)


class TestSanitizeFilename:
    def test_plain_name_unchanged(self):
        assert sanitize_filename("Contract 2025.pdf") == "Contract 2025.pdf"

    def test_path_components_stripped(self):
        assert sanitize_filename("../../etc/passwd") == "passwd"
        win_path = "C:" + chr(92) + "Users" + chr(92) + "someone" + chr(92) + "file.txt"
        assert sanitize_filename(win_path) == "file.txt"

    def test_unsafe_characters_replaced(self):
        assert sanitize_filename("my<>file:.pdf") == "my_file_.pdf"

    def test_dotslash_rejected(self):
        with pytest.raises(InvalidFilename):
            sanitize_filename("..")

    def test_empty_rejected(self):
        with pytest.raises(InvalidFilename):
            sanitize_filename("   ")

    def test_length_capped(self):
        name = sanitize_filename("a" * 300 + ".txt")
        assert len(name) <= 150


class TestValidateUpload:
    def test_valid_txt(self):
        assert validate_upload("doc.txt", 100) == "doc.txt"

    def test_unsupported_extension(self):
        with pytest.raises(UnsupportedFileType):
            validate_upload("malware.exe", 100)

    def test_no_extension(self):
        with pytest.raises(UnsupportedFileType):
            validate_upload("README", 100)

    def test_too_large(self, settings):
        with pytest.raises(FileTooLarge):
            validate_upload("big.pdf", (settings.max_upload_mb + 1) * 1024 * 1024, settings)

    def test_empty_file(self):
        with pytest.raises(EmptyFileError):
            validate_upload("empty.txt", 0)


class TestSaveUpload:
    def test_saves_under_generated_id(self, settings):
        content = b"hello contract"
        path, internal_id, display = save_upload(content, "../../weird name.TXT", settings)
        assert internal_id != "weird name.TXT"
        assert path.exists() and path.read_bytes() == content
        assert display == "weird name.TXT"
        assert path.parent == settings.upload_dir.resolve()
        delete_stored_file(path)

    def test_rejects_exe(self, settings):
        with pytest.raises(UnsupportedFileType):
            save_upload(b"MZ...", "tool.exe", settings)


def test_cleanup_temp_files(settings, tmp_path):
    import time

    old = settings.temp_dir / "old.bin"
    new = settings.temp_dir / "new.bin"
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    old.write_bytes(b"x")
    new.write_bytes(b"x")
    age = time.time() - 5 * 3600
    import os

    os.utime(old, (age, age))
    assert cleanup_temp_files(1, settings) == 1
    assert not old.exists() and new.exists()
