# ContractIQ — Phase 4 Document Parser Report

_Generated: 2026-08-31 · All behaviours verified by automated tests (`backend/tests/test_document_parser.py`)._

## Supported formats

| Format | Library | Notes |
|---|---|---|
| PDF | PyMuPDF 1.26.7 (already installed) | multi-page text extraction, page count, metadata |
| DOCX | python-docx 1.2.0 (installed this phase) | paragraphs + table cells joined with `\|`, line breaks preserved |
| TXT | Python stdlib | UTF-8 first, graceful fallback `utf-8-sig` → `cp1252` → `latin-1` with a warning |

## Standard output

`ParsedDocument`: `filename, original_filename, file_type, text, character_count, page_count, metadata, warnings, ocr_required`.

## Edge cases handled (each covered by a test)

| Case | Behaviour |
|---|---|
| Normal / multi-page PDF | text joined across pages, page count recorded |
| Empty TXT / empty DOCX | `EmptyDocument` |
| Zero-page PDF | `EmptyDocument` |
| Corrupt PDF / corrupt DOCX | `CorruptDocument` (no crash, no repair attempts) |
| Encrypted PDF (AES-128 fixture) | `EncryptedDocument` — password-protected files are refused, never brute-forced |
| Scanned / image-only PDF (image fixture, no text layer) | `OcrRequiredError` with an explicit message; **OCR is never faked** and remains an optional future module |
| Non-UTF-8 TXT | fallback decoding + warning recorded in metadata |
| Unsupported extension (.html/.exe/none) | `UnsupportedFileType` |

## Safety properties

- Documents are treated as untrusted data: text extraction only, no content execution, no macro/embedded-object handling (python-docx reads XML parts only).
- Filenames never reach the filesystem: storage uses generated UUID ids (`storage/uploads/<uuid>.<ext>`), display names are sanitized (`app/utils/files.py`).
- `PDF_MIN_TEXT_CHARS = 20` separates "scanned" from "has text" — below it the parser reports the scanned state instead of returning garbage.

## Measured timings (smoke flow, `reports/phase4_smoke_flow.json`)

- Parse synthetic 706-char DOCX: < 0.1 s
- Full smoke flow (parse → real-model analysis → risk → SQLite persist → reload): 89.4 s total, of which the first analysis includes one-time CUDA/model load; steady-state per-contract model time is ~4 s (Phase 3 test run measured 102 contracts at ~4 s each).
