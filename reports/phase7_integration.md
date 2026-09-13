# ContractIQ — Phase 7 Integration Hardening Report

_Generated: 2026-09-05 · 174 backend/ML tests ✅ · 13 frontend tests ✅ · build ✅ · lint ✅ · live E2E ✅ · offline E2E ✅._

## API contract audit

All frontend calls were audited against the FastAPI routes/Pydantic schemas (`/health`, `/contracts/upload`, `/contracts`, `/contracts/{id}`, `/{id}/text`, `/{id}/analyze`, `/{id}/analysis`, `/analyses/{id}`, `/stats`). Multipart field name `upload` ✓, error envelope shape ✓, pagination params ✓, stats schema ✓. Findings:

- `duplicate_of_id` was missing from the frontend `Contract` type usage in the workspace header — added a "duplicate" chip (§22: duplicates are allowed but clearly surfaced).
- Error codes were already consistent; added the new `ANALYSIS_IN_PROGRESS` code to the friendly-message map.

## Workflow hardening (backend)

- **Re-analysis policy (Option A, documented):** analyzing a COMPLETED contract returns the existing latest analysis (idempotent — no duplicate analysis versions). While running: `409 ANALYSIS_IN_PROGRESS`.
- **Stale-ANALYZING recovery:** on startup the app marks analyses stuck in `ANALYZING` (process crash) as `FAILED` ("interrupted by application restart; safe to retry") and the contract becomes retryable. Startup log: `stale_analyses_recovered`.
- **CUDA OOM safety:** `torch.cuda.OutOfMemoryError` is caught specifically, the CUDA cache is cleared, the analysis is marked FAILED with a clear message, and the server keeps serving (no Uvicorn crash).
- **Model singleton re-verified:** the analyzer is created once per process at startup and loads lazily once; health never loads it (log evidence: single model-load line per process; analysis events reference the cached instance).

## Workflow hardening (frontend)

- **Request locking:** the detail-page Analyze action and the upload flow use a ref-based lock + disabled buttons — double-submission is impossible.
- **Stale-response prevention:** `useAsyncData` carries a per-run `cancelled` flag (older responses can never overwrite newer ones; no updates after unmount). StrictMode double-invocation only repeats idempotent GETs.
- **Timeout strategy (per endpoint class):** health 8 s · list/detail/text/stats 15 s · upload+parse 60 s · **analysis 300 s** (never a false failure while the model is still working).
- **Status recovery on refresh/reopen:** the detail page reloads contract + latest analysis + raw text and handles every status: COMPLETED → workspace, FAILED → failure banner with explicit "Retry analysis", ANALYZING → calm 4 s status polling that auto-reveals the workspace when done, READY/UPLOADED → "Analyze contract" action (added this phase).
- **Offline recovery:** health polling is 30 s online / 12 s offline with a manual "Retry now" button; the UI flips back to online without a page reload.
- **Elapsed time** is shown during analysis (wall-clock, honestly labeled — no fake percentages).

## Evidence consistency (critical invariant)

Integration tests assert `stored_text[start_char:end_char] == clause.text` for every found clause against `GET /api/contracts/{id}/text`, including edge cases: clause at document **beginning**, **end**, **multiline** evidence, **unicode** (Café, “quotes”, §, ✓), **repeated** sentences, and out-of-range clipping. All pass.

## Integration tests (18, `backend/tests/test_integration_phase7.py`)

Full flow · offsets-vs-text invariant + 5 edge cases · metadata-without-raw-text · idempotent re-analysis · failed-analysis retry · stale-ANALYZING startup recovery · model-unavailable 503 envelope · history/stats consistency · delete cascade + 404s · duplicate-upload flagging · CORS preflight + header · error-envelope shape on all error routes · health model-state.

## Live E2E result (`reports/phase7_e2e.json`, real model, no mocks)

upload → analyze (real engine) → workspace → RiskOrb (30/LOW, 2 findings) → click "Governing Law" → **exact highlight** → history → reopen without re-analysis → **browser refresh: state survives** → delete → row removed + deleted route handled cleanly → second contract → **backend killed → "Engine Offline" UI shown, page survives** → backend restarted (20.7 s) → **"Retry now" recovers the UI without reload** → detail-page Analyze runs the real model successfully (55 s).

## Timings & logging

API latency (warm): health 29 ms · list 45 ms · detail 19 ms · text 20 ms · analysis fetch 32 ms · stats 23 ms. Log audit: **zero** contract-text occurrences in backend logs; logs contain request IDs, routes, statuses, durations, analysis start/complete events. Frontend ships no console logging.

## Files changed

```
backend/app/services/contract_analysis.py   idempotent analyze, stale recovery, OOM handling
backend/app/core/exceptions.py              AnalysisInProgress (409)
backend/app/main.py                         startup recovery, 409 mapping
backend/tests/test_integration_phase7.py    18 integration tests (new)
frontend/src/services/api.ts                timeout strategy, 409 message
frontend/src/hooks/useEngine.ts             adaptive health polling + recheck()
frontend/src/App.tsx                        offline banner with Retry-now
frontend/src/pages/ContractDetailPage.tsx   status recovery, Analyze action + lock, ANALYZING poll, duplicate chip
frontend/src/pages/AnalyzePage.tsx          elapsed timer, duplicate note
frontend/src/components/EmptyState.tsx      children slot (for the Analyze action)
frontend/verify-phase7-e2e.mjs              live E2E + offline recovery script (new)
reports/phase7_e2e.json                     E2E evidence (new)
```

## Portability

Scan of all runtime source (py/ts/tsx/mjs/bat): **no** hardcoded `C:\proj2`, usernames, absolute DB/Node/Python paths or GPU ids — the E2E's own backend-restart command resolves the project root dynamically. Dependencies reproducible from `backend/requirements.txt`, `ml/requirements.txt`, `frontend/package-lock.json`; model loads from the bundled `ml/models/final` with a documented baseline fallback. `data.zip` SHA-256 verified unchanged.

## Known limitations

- The 13 browser-console "Failed to load resource" entries in the E2E are network-level logs of **expected** failure responses (404 deleted-route checks, ERR_CONNECTION_REFUSED during the intentional offline window, 500 for failed-analysis retrieval) — the UI handles each gracefully; page errors remain 0.
- Analysis is still synchronous (by design); the detail page's 4 s status polling covers cross-tab/refresh recovery without job infrastructure.
- GPU OOM path is implemented and unit-reviewed but was not physically triggered on this 4 GB card (would require a deliberately oversized document).
