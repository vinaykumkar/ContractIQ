# ContractIQ — Phase 9 Packaging & Portability Report

_Generated: 2026-09-05 · Phase 9 of 9 — COMPLETE · Project status: **9/9**_

## What was delivered

| Item | File |
|---|---|
| One-click installer | `setup_windows.bat` (Python/Node detection + version guard, `.venv` creation, GPU-prompted official PyTorch install, requirements, npm ci, storage dirs, `.env` creation, DB init, bundled-model + import verification) |
| Launchers (upgraded) | `run_backend.bat`, `run_frontend.bat`, `run_contractiq.bat` (browser auto-open) — all `%~dp0`-relative, all show a clear "run setup first" message instead of confusing errors |
| Safe stopper | `stop_contractiq.bat` (window-title filtered — never kills unrelated Python/Node) |
| Verification scripts | `scripts/check_portability.py` (PASS: 150 files), `scripts/system_check.py` (PASS), `scripts/verify_install.py` (PASS; called by setup) |
| Documentation | `README.md` (rewritten), `docs/USER_GUIDE.md`, `docs/ARCHITECTURE.md`, `docs/ML_MODEL.md`, `docs/RISK_SCORING.md`, `docs/TROUBLESHOOTING.md`, `docs/DEPLOYMENT.md`, `docs/RUNTIME_ONLY_PACKAGE.md`, `docs/SECURITY.md`, `TRANSFER_TO_ANOTHER_LAPTOP.md`, `THIRD_PARTY_NOTICES.md`, `FINAL_RELEASE_CHECKLIST.md` |
| Version constraints | Python **3.11–3.13** (tested 3.11.9, enforced by setup); Node **20+** (tested v24.12.0, `.nvmrc`=24) |

## Portability test (the critical verification) — PASSED

Method: the project was **copied to `C:\Temp\Contract IQ Test 2026`** — a path
containing spaces, outside the original folder — excluding `.venv`,
`node_modules`, `.git`, caches, database and uploads.

1. **`setup_windows.bat` in the copy**: genuine fresh install — created a new
   `.venv`, installed the CUDA PyTorch build + all requirements (wheels from
   local cache), `npm ci` from the lockfile, storage + `.env` + DB creation,
   model verification, import checks → **"setup finished successfully"**.
2. **`run_contractiq.bat` in the copy** with `HF_HUB_OFFLINE=1` (proving no
   Hugging Face cache dependence): backend + frontend healthy; **fresh
   `contractiq.db` created inside the copied folder's storage**; model state
   `fine_tuned` from the copied `ml/models/final`.
3. **Real analysis in the copy** (bundled model, offline): upload → 9.0 s
   analysis → risk 40/MEDIUM → 3 clauses found → **0 evidence-offset
   mismatches**.
4. **Relative-path proof:** uploads and DB were written to the *copied*
   folder; the original `C:\proj2` storage was untouched (mtime + content
   checks).
5. **Frontend build in the copy**: `npm run build` ✅.
6. **`stop_contractiq.bat`** stopped both title-filtered windows safely.

Two real portability bugs were found and fixed during this test:

- **Missing dependency:** `scikit-learn` (retrieval stage) was not declared in
  any requirements file — worked only via a globally installed package. Added
  to `ml/requirements.txt` + `verify_install` import check.
- **Batch parser bugs in setup:** unescaped parentheses in `echo` lines inside
  if-blocks aborted the script mid-flow. Fixed; full setup re-run verified.

## Model & licensing

- Bundled model: `ml/models/final/` — 128 MB (weights 133 MB safetensors,
  tokenizer, config, training metadata). Loads project-relatively; no HF cache
  required (verified under `HF_HUB_OFFLINE=1`).
- Base model `deepset/minilm-uncased-squad2`: **CC-BY-4.0** — redistribution
  permitted with attribution (provided in `THIRD_PARTY_NOTICES.md`).
- GitHub note: `model.safetensors` exceeds the 100 MB per-file limit → use
  Git LFS or a Release asset (documented in `FINAL_RELEASE_CHECKLIST.md` /
  `docs/DEPLOYMENT.md`).
- Project license: none chosen — documented as "all rights reserved until a
  license is selected" (no license was invented).

## Sizes

| Category | Size |
|---|---:|
| Whole folder (as-is, incl. .venv 3.6 GB + node_modules 0.2 GB) | ~4.4 GB |
| Transferable folder (excl. .venv/node_modules/caches) | ~0.5 GB |
| — model (ml/models/final) | 128 MB |
| — dataset assets (data.zip + raw + processed) | ~230 MB |
| — source + docs + reports + storage | ~10 MB |

Runtime-only package (see `docs/RUNTIME_ONLY_PACKAGE.md`) drops dataset and
checkpoint assets → ~0.5 GB.

## Final verification (original project, post-packaging)

- pytest backend + ML: **186 passed** (incl. 12 Phase 8 QA tests, 18 Phase 7
  integration tests)
- frontend vitest: **13 passed** · build ✅ · lint ✅
- `check_portability.py`: **PASS** (150 runtime files) · `system_check.py`: PASS
- Final real smoke via launcher: upload → analyze (31 s) → risk 40/MEDIUM →
  0 evidence mismatches → cleanup ✅
- `data.zip` SHA-256: unchanged.

## Verdict

**READY.** ContractIQ is 9/9 complete: portable (fresh-folder + spaces-path
tested), reproducible from manifests, documented, GitHub-prepared (model size
note included), free-only, GPU/CPU auto-switching, with zero release blockers.
