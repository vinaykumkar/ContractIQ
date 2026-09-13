# ContractIQ — Phase 5 Backend (FastAPI) Report

_Generated: 2026-09-02 · Verified by `backend/tests/test_api.py` (26 tests) and one real integration smoke run (`scripts/phase5_smoke_api.py` → `reports/phase5_smoke_api.json`)._

## Routes (all under `/api`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | app/db/model status (model state read from config — **no model load**) |
| POST | `/api/contracts/upload` | validate → safe-store → parse → `Contract` row (`READY`); no auto-analysis |
| GET | `/api/contracts` | pagination, `search`, `status` filter, `risk_level` filter, `sort` (validated) |
| GET | `/api/contracts/{id}` | metadata + latest-analysis summary (no raw text) |
| GET | `/api/contracts/{id}/text` | raw parsed text for Phase 6 highlighting (404 `RAW_TEXT_UNAVAILABLE` when disabled) |
| POST | `/api/contracts/{id}/analyze` | ML extraction + heuristic risk + transactional persistence |
| GET | `/api/contracts/{id}/analysis` | latest analysis: overall risk, clauses, evidence, findings, entities |
| GET | `/api/analyses/{analysis_id}` | fetch one analysis by id |
| DELETE | `/api/contracts/{id}` | contract + cascades + stored upload file (containment-guarded) |
| GET | `/api/stats` | contracts/completed/failed counts, risk distribution, avg processing ms, clauses detected |

OpenAPI: `/docs`, `/redoc`, `/openapi.json` all verified live (status 200) and by test.

## Files created/modified

```
backend/app/main.py                  app factory (create_app), lifespan, CORS, error handlers, request-ID middleware
backend/app/api/deps.py              settings/service deps, model-health (config-only), request-id contextvar
backend/app/api/router.py            /api router assembly
backend/app/api/routes/health.py     health route
backend/app/api/routes/contracts.py  contract/analysis/stats routes + entity derivation
backend/app/core/logging.py          structured event logging (ids/counts/durations only)
backend/app/schemas/common|contract|analysis.py   typed Pydantic responses
backend/app/db/repository.py         (extended) pagination/sort/status/stats
backend/app/services/contract_analysis.py  (extended) READY status, delete, analysis-by-id, listing/detail/raw-text helpers
backend/requirements.txt             + fastapi, uvicorn
run_backend.bat                      portable launcher (dynamic project dir, optional venv)
.env.example                         all CONTRACTIQ_* variables documented
scripts/phase5_smoke_api.py          real integration smoke
backend/tests/test_api.py            26 API tests
```

No Phase 4 logic was duplicated — routes orchestrate the existing parser/ML-adapter/risk-engine/repository.

## Test count & results

- **26 API tests** (all passing): health, OpenAPI, upload TXT/PDF/DOCX, invalid extension, empty file, scanned PDF (`OCR_REQUIRED`), corrupt PDF, traversal-filename sanitization, listing/search/status-filter (+invalid-param 422), detail (no raw text), analysis success + persistence, analysis-by-id, model-unavailable (503 + FAILED persisted), generic analysis failure (500, concise message, retrievable FAILED analysis), raw text on/off, delete (cascade + 404s), stats, error envelope + `X-Request-ID`, CORS header, and test/demo-DB isolation.
- Combined suite: **156 passed** (63 ML + 67 backend/service + 26 API) in ~47 s.

## Real smoke result

`scripts/phase5_smoke_api.py` (own temp DB, real fine-tuned model): tiny TXT → upload (real parser) → analyze (**18.5 s incl. one-time model load**; risk 27/LOW) → 8 clauses found (governing_law 0.989, agreement_date 0.984, termination 0.984, renewal 0.935), entities extracted, rules fired (`AUTO_RENEWAL_LANGUAGE`, `CAP_ON_LIABILITY_ABSENT`, …), evidence substring check passed, stats/list/delete verified, `/docs` 200.

## Model loading strategy

`MLAnalyzerAdapter` is created once per app process at startup and loads the transformer **lazily on first analysis**; the instance is kept on CUDA/CPU between requests. Health never triggers a load. No duplicate model copies are created (CUDA OOM surfaces as a safe 500 envelope, not a crash).

## Database strategy

App factory builds one engine from `CONTRACTIQ_DB_URL` (default project-relative `storage/contractiq.db`); schema init is idempotent at startup, never destructive. Tests use per-test temp SQLite files (verified: tests never touch the demo DB). Analysis persistence stays transactional (rollback verified in Phase 4 tests); lifespan disposes both the app and the service engine (Windows file-lock issue found and fixed in the smoke run).

## Measured simple-endpoint timings (real smoke run)

health 4–40 ms · upload+parse ~15 ms · analysis fetch ~2 ms · stats+list ~42 ms · analysis 18.5 s (model, first load; steady-state ≈ 4 s per Phase 3).

## Error handling & security

Consistent envelope `{"error", "message", "request_id"}` for every non-2xx: 400 (bad type/empty file/invalid name), 404 (contract/analysis/raw-text), 413 (oversized), 422 (validation/parse/scanned/encrypted), 500 (analysis/database/internal), 503 (model unavailable). Raw tracebacks never leave the server. Request-ID middleware echoes `X-Request-ID` and threads it through logs. Portability scan of all runtime source: **clean**; `data.zip` SHA-256 verified unchanged.

## Known limitations

- Analysis is synchronous within the request (by design for this phase; statuses `ANALYZING/COMPLETED/FAILED` already support Phase 7 polling/streaming).
- No authentication (explicitly deferred); CORS limited to localhost dev origins by default.
- `AVG` over a single instant mock analysis exposed a 0-value edge (fixed); mock-analyzed contracts can report `avg_processing_ms` ≈ 0.
- Single uvicorn process: GPU memory is shared by one model instance only (correct for this scale).

## Backend startup (exact)

```
run_backend.bat
:: or manually, from the backend/ directory:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
