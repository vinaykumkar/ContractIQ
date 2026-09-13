# ContractIQ — Runtime-Only Package

The full project folder contains **development/training assets** that the
finished application does not need at runtime. If you only want to *run*
ContractIQ, these may be excluded when copying:

| Path | Size (approx.) | Why it is not needed at runtime |
|---|---|---|
| `data.zip` | 18 MB | source dataset; the model is already trained |
| `data/raw/` | ~80 MB | extracted CUAD JSON (training input) |
| `data/processed/` | ~150 MB | tokenized training features (Parquet) |
| `ml/checkpoints/` | ~130–500 MB | training checkpoints (best model is in `ml/models/final/`) |
| `reports/` | < 1 MB | phase reports (keep if you want the evidence trail) |
| `frontend/shots/` | ~2 MB | QA screenshots |

**Required for runtime** (never remove):

- `ml/models/final/` — the bundled fine-tuned model (~128 MB)
- `backend/`, `frontend/`, `ml/configs/`, `ml/src/device.py + inference deps`
- `scripts/verify_install.py` (used by setup)
- `storage/` (auto-created; keep `contractiq.db` to preserve history)
- `.env.example`, `setup_windows.bat`, `run_*.bat`

Nothing in the runtime code reads `data/` or `ml/checkpoints/` — removing them
is safe; they are kept in the primary project for reproducibility of training.

Result: a runtime-only copy is roughly **~0.5 GB** (dominated by the model and
freshly installed dependencies) instead of ~1 GB+.
