# ContractIQ — Final Release Checklist

_Status: Phase 9 complete. Evidence in `reports/phase8_final_qa.json`,
`reports/phase8_e2e.json`, `reports/phase7_e2e.json`, `reports/phase9_portability_test.md`._

- [x] setup_windows.bat (fresh .venv, requirements, GPU-detect, storage, verify)
- [x] run_backend.bat (project-relative, .venv-aware, first-run message)
- [x] run_frontend.bat (node_modules check, first-run message)
- [x] run_contractiq.bat (combined launch + browser open)
- [x] stop_contractiq.bat (window-title filtered, safe)
- [x] bundled model in ml/models/final (weights, tokenizer, config, metadata)
- [x] model loads from project folder (no HF cache dependency — verified in copied-folder test)
- [x] GPU auto-detection (CUDA used when present)
- [x] CPU fallback (verified)
- [x] SQLite fresh initialization on first run (verified in copied folder)
- [x] docs: README, USER_GUIDE, ARCHITECTURE, ML_MODEL, RISK_SCORING, SECURITY, TROUBLESHOOTING, DEPLOYMENT, RUNTIME_ONLY_PACKAGE
- [x] TRANSFER_TO_ANOTHER_LAPTOP.md
- [x] THIRD_PARTY_NOTICES.md (licenses verified)
- [x] portability test: fresh copy at `C:\Temp\Contract IQ Test 2026` (path WITH spaces) — setup + launch + upload + real analysis + evidence check all passed; zero writes to the original folder
- [x] no hardcoded machine paths (scripts/check_portability.py → PASS, 150 files)
- [x] no secrets (scan clean)
- [x] all automated tests pass (186 backend/ML + 13 frontend)
- [x] frontend build + lint pass
- [x] real smoke test passes (upload → analyze → evidence → delete)
- [x] GitHub-safe .gitignore (model file >100 MB → documented Git LFS option)
- [x] release blockers = zero

## GitHub publishing note

`ml/models/final/model.safetensors` is ~133 MB — above GitHub's 100 MB
per-file limit. Choose one (documented in `docs/DEPLOYMENT.md`):
1. Git LFS for `ml/models/final/*.safetensors`, or
2. attach the model as a GitHub Release asset with a setup download step, or
3. distribute the folder directly (transfer guide).

## Post-release additions (September 2026)

- [x] production single-port serving: FastAPI serves `frontend/dist` with SPA
      fallback (`app/main.py`); launchers `run_contractiq_prod.bat` (localhost)
      and `run_contractiq_lan.bat` (LAN, no auth — trusted networks only)
- [x] default production port 8010 (8000 collides with another project on the
      dev machine); override via `BACKEND_PORT`
- [x] production frontend uses same-origin `/api` base (works on any host/port
      without rebuilding); dev mode unchanged (`VITE_API_BASE_URL` default)
- [x] CPU fallback hardening: CUDA-built torch with an incompatible NVIDIA
      driver no longer crashes the backend (eager attention + stubbed CUDA
      stream probe, `ml/src/inference.py`)
