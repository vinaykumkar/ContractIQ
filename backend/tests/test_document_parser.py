"""Document parser tests: TXT/DOCX/PDF happy paths and edge cases."""
from __future__ import annotations

import pytest

from app.core.exceptions import (
    CorruptDocument,
    EmptyDocument,
    EncryptedDocument,
    OcrRequiredError,
    UnsupportedFileType,
)
from app.services.document_parser import parse_document, parse_txt


class TestTxt:
    def test_parse_utf8(self, sample_txt):
        doc = parse_document(sample_txt, "sample contract.txt")
        assert doc.file_type == "txt"
        assert "Distribution Agreement" in doc.text
        assert doc.character_count == len(doc.text)
        assert doc.page_count is None
        assert not doc.is_empty

    def test_fallback_encoding(self, tmp_path):
        p = tmp_path / "cp1252.txt"
        p.write_bytes("caf\xe9 clause".encode("cp1252"))
        doc = parse_document(p, "cp1252.txt")
        assert "clause" in doc.text
        assert any("fallback" in w for w in doc.warnings)

    def test_empty_txt(self, tmp_path):
        p = tmp_path / "empty.txt"
        p.write_text("   \n  ")
        with pytest.raises(EmptyDocument):
            parse_document(p)


class TestDocx:
    def test_parse_paragraphs_and_tables(self, sample_docx):
        doc = parse_document(sample_docx, "sample_contract.docx")
        assert doc.file_type == "docx"
        assert "Distribution Agreement" in doc.text
        assert "Alpha Corp" in doc.text  # from the table
        assert doc.metadata["tables"] == 1

    def test_empty_docx(self, tmp_path):
        import docx

        d = docx.Document()
        p = tmp_path / "empty.docx"
        d.save(str(p))
        with pytest.raises(EmptyDocument):
            parse_document(p)

    def test_corrupt_docx(self, tmp_path):
        p = tmp_path / "bad.docx"
        p.write_bytes(b"PK\x03\x04 not a real docx")
        with pytest.raises(CorruptDocument):
            parse_document(p)


class TestPdf:
    def test_parse_multipage(self, sample_pdf):
        doc = parse_document(sample_pdf, "sample_contract.pdf")
        assert doc.file_type == "pdf"
        assert doc.page_count and doc.page_count >= 2
        assert "Distribution Agreement" in doc.text

    def test_scanned_pdf_raises_ocr_required(self, scanned_pdf):
        with pytest.raises(OcrRequiredError, match="OCR"):
            parse_document(scanned_pdf)

    def test_corrupt_pdf(self, corrupt_pdf):
        with pytest.raises((CorruptDocument, OcrRequiredError)):
            parse_document(corrupt_pdf)

    def test_encrypted_pdf(self, encrypted_pdf):
        with pytest.raises(EncryptedDocument):
            parse_document(encrypted_pdf)

    def test_empty_pdf(self, tmp_path):
        """A structurally-minimal PDF with zero pages -> EmptyDocument (or scanned-state)."""
        p = tmp_path / "empty.pdf"
        p.write_bytes(b"%PDF-1.4\n%%EOF\n")  # PyMuPDF cannot save zero-page docs
        with pytest.raises((EmptyDocument, OcrRequiredError, CorruptDocument)):
            parse_document(p)


def test_unsupported_extension(tmp_path):
    p = tmp_path / "file.html"
    p.write_text("<html></html>")
    with pytest.raises(UnsupportedFileType):
        parse_document(p)


def test_parse_txt_direct(sample_txt):
    doc = parse_txt(sample_txt, "s.txt")
    assert doc.file_type == "txt"
