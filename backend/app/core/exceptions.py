"""Domain-specific backend exceptions.

The future API layer (Phase 5) maps these to clean HTTP error responses;
raw stack traces must never reach API users.
"""
from __future__ import annotations


class ContractIQError(Exception):
    """Base class for all ContractIQ domain errors."""

    code = "contractiq_error"
    message = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message


# ---- document / file safety -------------------------------------------------

class UnsupportedFileType(ContractIQError):
    code = "unsupported_file_type"
    message = "Unsupported file type. Allowed: PDF, DOCX, TXT."


class FileTooLarge(ContractIQError):
    code = "file_too_large"
    message = "The uploaded file exceeds the maximum allowed size."


class EmptyFileError(ContractIQError):
    code = "empty_file"
    message = "The uploaded file is empty."


class InvalidFilename(ContractIQError):
    code = "invalid_filename"
    message = "The provided filename is invalid or unsafe."


class ParseError(ContractIQError):
    code = "parse_error"
    message = "The document could not be parsed."


class EmptyDocument(ParseError):
    code = "empty_document"
    message = "The document contains no readable text."


class CorruptDocument(ParseError):
    code = "corrupt_document"
    message = "The document appears to be corrupt or malformed."


class EncryptedDocument(ParseError):
    code = "encrypted_document"
    message = "The document is encrypted/password-protected and cannot be read."


class OcrRequiredError(ParseError):
    code = "ocr_required"
    message = "No text layer found (likely a scanned/image-only PDF). OCR is not enabled."


# ---- analysis / ML -----------------------------------------------------------

class ModelUnavailable(ContractIQError):
    code = "model_unavailable"
    message = "The QA model is not available. Set up ml/models/final or the baseline model."


class AnalysisFailure(ContractIQError):
    code = "ANALYSIS_FAILURE"
    message = "Contract analysis failed."


class AnalysisInProgress(ContractIQError):
    code = "ANALYSIS_IN_PROGRESS"
    message = "An analysis for this contract is already running."


# ---- persistence -------------------------------------------------------------

class DatabaseFailure(ContractIQError):
    code = "database_failure"
    message = "A database operation failed."


class ContractNotFound(ContractIQError):
    code = "CONTRACT_NOT_FOUND"
    message = "Contract was not found."


class RawTextUnavailable(ContractIQError):
    code = "RAW_TEXT_UNAVAILABLE"
    message = "Raw text is not stored for this contract (STORE_RAW_TEXT disabled)."
