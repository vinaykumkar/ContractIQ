# ContractIQ — Phase 8 Final QA Report

_Generated: 2026-09-05 · Phase: 8 of 9 (final packaging pending)_
_Machine-readable twin: `reports/phase8_final_qa.json` · E2E evidence: `reports/phase8_e2e.json`_

## Environment / GPU

- GPU: **NVIDIA GeForce RTX 2050, 4 GB** · PyTorch **2.13.0+cu130** · CUDA runtime **13.0** · inference device **cuda**
- Model state: **fine_tuned** (`ml/models/final`, CUAD 1-epoch MiniLM, thresholds frozen in Phase 3)

## 1. Clean start

From a fully stopped state (all processes killed): `run_contractiq.bat` brought **backend + frontend to 200 OK in 16 s**. Verified twice during the phase (once after the delete-FK fix).

## 2. Main user journey (real model, 22 steps)

All steps passed (`reports/phase8_e2e.json` → `journey`): upload (720 chars, READY) → metadata → analyze (**36.3 s** incl. cold model load) → Risk Orb (60/MEDIUM, 5 findings) → Clause Intelligence Map (visible, nodes active) → entities → clause cards → risk findings → click "Governing Law" → **exact highlight** → click "Non-Compete" → **highlight moved correctly** → history → reopen without re-analysis → browser refresh → state restored → delete → stats updated. Screenshot: `frontend/shots/p8-workspace.png`.

## 3–7. File formats & edge cases

| Test | Result |
|---|---|
| TXT upload → analyze → evidence invariant → reopen | ✅ (3.6 s analysis) |
| PDF (hand-crafted valid text PDF) → analyze → evidence | ✅ (3.7 s) |
| DOCX | ✅ via Phase 4/5 suites (tables + paragraphs); exercised live in Phase 4 smoke |
| Empty file / unsupported ext / traversal filename | ✅ clean 400s, name sanitized |
| Corrupt PDF | ✅ 422 CORRUPT_DOCUMENT |
| Scanned/image-only PDF | ✅ OCR_REQUIRED state (Phase 4 suite) |
| Encrypted PDF | ✅ ENCRYPTED_DOCUMENT (Phase 4 suite) |
| Unicode/Hindi TXT | ✅ parsed without encoding crash |
| Duplicate upload | ✅ both kept, second flagged `duplicate_of_id` + UI "duplicate" chip |
| Oversized | ✅ 413 (backend unit test) |

## 8. Large contract

**197,160-char** synthetic contract (~10× the median CUAD document): analysis **16.9 s** on GPU, document renders with only 3 `<mark>` nodes in the DOM (highlight-scoped rendering), scroll responsive (384 ms round-trip to bottom), deep-document highlight exact, browser stayed responsive. Zero console errors during the whole battery.

## 9. Evidence invariant (ZERO mismatches required)

- Browser battery: 14 found clauses across journey + TXT + PDF + large contract — **0 mismatches**
- Whole demo DB sweep: **115 found-clause rows** across all completed analyses — **0 mismatches**
- Unicode, multiline, start/end-of-document, repeated phrases covered by regression tests. **Requirement met.**

## 10–14. Risk engine / concurrency / recovery

- Band boundaries verified with exact synthetic scores: 22→LOW, 30→LOW, 33→MEDIUM, 60→MEDIUM, 63→HIGH; max reachable 89; clamp 0–100 holds.
- Confidence-aware: found+low-confidence → `uncertain`, weight 0, severity untouched, ML confidence reported separately.
- Idempotency: re-analyzing COMPLETED returns the same analysis id.
- Concurrency: latest-ANALYZING → **409 ANALYSIS_IN_PROGRESS**.
- Crash recovery: stale ANALYZING rows → FAILED at startup, retryable (test + Phase 7 live verification).
- Offline: frontend survives, banner shows, "Retry now" recovers without reload (Phase 7 live E2E re-confirmed).

## 15–20. Device, DB, persistence

- **Model loads once** per process: singleton identity verified; first analysis 1.5 s vs 0.7 s second (no reload).
- **VRAM stable**: 0.0 → 0.141 GB after analysis; no growth across repeats.
- **Leak smoke**: RSS growth **0.0 MB** over 50 light requests.
- **CPU fallback**: `device='cpu'` smoke works (0.6 s).
- **DB integrity**: zero orphan analyses/clause-results/risk-findings; delete cascade leaves all four tables empty; **restart persistence** verified (rows survive app recreation).
- **STORE_RAW_TEXT=false**: text endpoint 404 RAW_TEXT_UNAVAILABLE; analyze fails cleanly to FAILED status.

## 21–24. Security, performance, suites

- Secret scan: **clean** · Log privacy: **no contract text** in backend logs · Portability scan: **clean** (incl. the E2E script itself).
- Timings: clean start 16 s · upload 159 ms · health 29 ms · list 45 ms · detail 19 ms · stats 23 ms · analysis 1.5–36 s (GPU, length-dependent) · reopen-after-refresh 1.6 s.
- **Tests: 186 backend/ML + 13 frontend = 199 passing.** Build ✅ (135 kB gzip), lint ✅ 0/0.

## 25. Bugs found & fixed this phase

| Bug | Severity | Fix + regression |
|---|---|---|
| No-raw-text analyze path raised inside its transaction → rollback silently discarded the FAILED status (contract stuck READY) | **HIGH** | commit-before-raise restructure + `TestRawTextDisabled` regression |
| Deleting a contract referenced by others' `duplicate_of_id` → FK violation → 500, deletion impossible | **HIGH** | reference cleared before delete + regression test; verified live on the 4 stuck rows |
| `AnalysisInProgress` raised but never imported (NameError on concurrent-analyze path) | **HIGH** (would 500 instead of 409) | import fixed; covered by 409 test |

## 26. Remaining issues (none BLOCKER)

- LOW: analysis is synchronous; a 5-min GPU stall would hold one request open (mitigated by 300 s client timeout + 409 guard + recovery).
- LOW: GPU-OOM path is tested via mocked exception, not a physical OOM (unsafe to force on 4 GB).
- COSMETIC: browser logs "Failed to load resource" network lines during intentional failure tests (handled in UI).
- LOW: QA-run contracts removed from the demo DB; one Phase 4 smoke DOCX kept as demo fixture.

**No release blockers remain.**
