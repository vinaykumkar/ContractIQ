# ContractIQ — Phase 4 Database Report

_Generated: 2026-08-31 · Verified by `backend/tests/test_database.py` (14 tests) and `test_contract_analysis.py` (13 tests)._

## Stack

SQLite + SQLAlchemy 2.0 (ORM, typed `DeclarativeBase`), zero server, fully portable.

## Location & configuration

- Default: **`storage/contractiq.db`** — resolved relative to the project root at runtime (`sqlite:///storage/contractiq.db`), never a hardcoded absolute path.
- Override: `CONTRACTIQ_DB_URL` (any SQLAlchemy URL; tests use per-test temp SQLite files).
- `PRAGMA foreign_keys=ON` is set per connection; schema creation is idempotent (`init_db`).

## Schema

| Table | Key columns |
|---|---|
| `contracts` | `id` (uuid-hex PK), `filename` (sanitized), `original_filename`, `file_type`, `created_at`, `status` (UPLOADED/PARSING/ANALYZING/COMPLETED/FAILED), `character_count`, `page_count`, `text_hash` (indexed, sha256 of normalized text), `parser_warnings` (JSON), `stored_path`, `raw_text` (**only when `STORE_RAW_TEXT=true`**), `duplicate_of_id` (self-FK) |
| `analyses` | `id`, `contract_id` FK, `model_name/model_version/model_state`, `started_at`, `completed_at`, `processing_ms`, `overall_risk_score`, `overall_risk_level`, `status` (ANALYZING/COMPLETED/FAILED), `error_message`, `disclaimer` |
| `clause_results` | `id`, `analysis_id` FK, `clause_type`, `found`, `extracted_text`, `confidence`, `start_char`, `end_char`, `risk_level`, `risk_reason`, `uncertain` |
| `risk_findings` | `id`, `analysis_id` FK, `rule_id`, `clause_type`, `severity`, `weight` (actually applied), `reason`, `evidence`, `confidence`, `uncertain` |

Deleting a contract cascades to its analyses, clause results and findings (verified).

## Repository layer

All queries live in `backend/app/db/repository.py`: `create_contract, get_contract, find_contract_by_hash, list_contracts (search/risk-level filter), update_contract_status, delete_contract, create_analysis, complete_analysis, fail_analysis, save_clause_results, save_risk_findings, get_analysis, latest_analysis, analyses_for_contract, stats_summary`.

## Transactions

`session_scope` commits on success and rolls back on any exception. Verified by tests: a mid-transaction crash leaves **no** contract row; a simulated persistence failure after clause writes leaves **no** analysis or clause rows. The model runs outside the transaction; its failure path records `status=FAILED` + `error_message` in a separate committed transaction.

## Duplicate detection / traceability

`text_hash` = SHA-256 of whitespace-normalized text. Re-ingesting identical text sets `duplicate_of_id` on the new contract (both remain analyzable; verified). Hashes are for dedup/traceability only — never security.

## Privacy

Full text is stored only when `CONTRACTIQ_STORE_RAW_TEXT=true` (default **on**, because the UI evidence-highlighting feature requires the original text; documented in `docs/SECURITY.md`). With it off, only metadata/results are persisted and analysis of old contracts is refused with a clean `FAILED` status rather than faked.

## Measured

- Schema creation + full analysis persistence chain (contract → analysis → 15 clause rows → findings → complete): fast, whole backend suite (67 tests incl. DB roundtrips) runs in ~30–55 s.
- `stats_summary()` returns contracts/analyses counts, average processing ms, risk-level distribution (used by Phase 5 `GET /api/stats`).
