# ContractIQ — Security Considerations

_Status: maintained since Phase 4. Applies to the document pipeline, ML layer, and database._

## Uploads are untrusted input

- **Allowed types only:** `.pdf`, `.docx`, `.txt` (extension + sanitized-name validation). Everything else is rejected with `UnsupportedFileType`.
- **Size limit:** `CONTRACTIQ_MAX_UPLOAD_MB` (default 20 MB); empty files rejected.
- **Filename handling:** user-supplied filenames are never used as storage paths. Storage names are generated UUID ids (`storage/uploads/<uuid>.<ext>`); display names pass through `sanitize_filename` (directory components stripped, unsafe characters replaced, traversal like `../../x` neutralized, hopeless names rejected).
- **Containment check:** the resolved storage path must remain inside the configured upload directory.
- **Never execute document content.** PDFs are read with PyMuPDF, DOCX with python-docx (XML parts only — macros/embedded objects are not opened), TXT is decoded as text. There is no OCR, no shell-outs, no templating of file content.

## Scanned / encrypted documents

- Encrypted (password-protected) PDFs are refused with `EncryptedDocument`; no password attempts are made.
- Text-less PDFs are reported as `OcrRequiredError` — the system never fabricates extracted text.

## ML layer

- The QA model is loaded from the local `ml/models/final` directory or the pinned baseline model id in `ml/configs/model.json`. **No user-supplied model paths or IDs are ever accepted at runtime** (no arbitrary-model-path execution from the frontend/API).
- Model inference never writes to the filesystem except designated model/cache directories.

## Database

- SQLite by default at `storage/contractiq.db` (project-relative); override via `CONTRACTIQ_DB_URL`. SQL access is exclusively through the SQLAlchemy repository layer with bound parameters — no string-built SQL.
- **No secrets are stored in the database.** Rows contain document metadata, analysis results, and heuristic risk findings only.
- **Raw contract text is stored only when `CONTRACTIQ_STORE_RAW_TEXT=true`** (default on, required by the evidence-highlighting UI). Turning it off keeps only metadata/results. `CONTRACTIQ_UPLOAD_RETENTION_HOURS` drives temp-file cleanup; uploaded originals can be deleted after analysis.
- `text_hash` (SHA-256 of normalized text) is used for duplicate detection/traceability only — not as an authentication or security mechanism.

## Error handling

- Domain exceptions (`app/core/exceptions.py`) carry stable codes; the future API layer maps them to clean responses. Raw stack traces are never returned to API users; unexpected errors are logged server-side with the message persisted as `analysis.error_message`.

## Configuration & secrets

- All configuration is environment-based with safe defaults (`.env` supported; `.env` is git-ignored; `.env.example` documents every variable). No credentials exist in this project — no paid APIs, no cloud services.

## Known limitations

- Single-user design; authentication/authorization is explicitly out of scope until a later phase (see README "Future improvements").
- SQLite is file-based: anyone with file access can read stored analyses — appropriate for a local/demo deployment, not for shared production hosting.
- Uploads are scanned by extension/size/name only; **no antivirus/malware scanning** is performed (uploads are never executed, which bounds the risk).
- **LAN mode (`run_contractiq_lan.bat`) exposes the app to every device on the network with no authentication** — anyone on the same Wi-Fi can upload contracts, trigger analyses, and read stored results. Use only on trusted networks; the default `run_contractiq_prod.bat` binding (localhost) is unaffected.
