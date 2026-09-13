# ContractIQ

**AI Contract Intelligence & Risk Analysis** — upload a contract, get clause extraction with exact evidence highlighting, transparent risk scoring, and an interactive analysis workspace.

> ContractIQ provides AI-assisted contract analysis and is not a substitute for professional legal advice.

## Features

- **AI-assisted contract analysis** — extractive QA model fine-tuned on the CUAD legal-contract dataset
- **Clause extraction** — 15 high-value clause types (Parties, Governing Law, Non-Compete, Liability Cap, …)
- **Exact evidence highlighting** — every finding links to its precise character range in the document
- **Risk scoring** — transparent, deterministic heuristic rules (0–100), clearly separated from AI confidence
- **Risk Orb** — animated risk visualization (score, level, findings)
- **Clause Intelligence Map** — signature SVG visualization of the contract and its clauses
- **PDF / DOCX / TXT** support with safe handling of corrupt, encrypted and scanned files
- **Contract history** — search, filter, reopen any previous analysis
- **GPU / CPU inference** — automatic device detection, no configuration needed
- **Local-first privacy** — everything runs on your machine; no cloud, no paid APIs

## Architecture

```
React + TypeScript + Vite  (frontend/)
        ↓ HTTP /api
FastAPI                    (backend/app/)
        ↓
Document Parser (PyMuPDF / python-docx)   → ContractAnalyzer (QA transformer)
        ↓                                  → Risk Engine (heuristic rules)
SQLAlchemy → SQLite (storage/contractiq.db)
```

See `docs/ARCHITECTURE.md` for the full picture.

## Supported clauses (Version 1)

Document Name · Parties · Agreement Date · Effective Date · Expiration Date · Renewal Term ·
Governing Law · Termination for Convenience · Non-Compete · Exclusivity · Anti-Assignment ·
License Grant · Audit Rights · Cap on Liability · Insurance

(the full 41-category CUAD registry is in `ml/configs/clauses.json`; enable more by flipping flags)

## Requirements

- Windows 10/11
- **Python 3.11 – 3.13** (tested on 3.11)
- **Node.js 20+** (tested on Node 24) — only for the frontend
- Optional: NVIDIA GPU + up-to-date driver (inference automatically uses CUDA; CPU works fine without)

## Fast setup

1. Copy/download this folder anywhere (e.g. `D:\Projects\ContractIQ`)
2. Double-click **`setup_windows.bat`** (creates `.venv`, installs all dependencies)
3. First run: build the production UI once — `cd frontend && npm run build`
4. Double-click **`run_contractiq_prod.bat`** (or **`run_contractiq_lan.bat`** to allow other devices on your Wi-Fi)
5. Open **http://127.0.0.1:8010**

## Manual setup

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt -r ml\requirements.txt
:: optional, for NVIDIA GPUs (official PyTorch index):
pip install "torch==2.13.0+cu130" --index-url https://download.pytorch.org/whl/cu130
cd frontend && npm ci && cd ..
copy .env.example .env
python scripts\verify_install.py
```

Run:

```bat
run_contractiq_prod.bat  :: production: built UI + API on one port, http://127.0.0.1:8010 (docs at /docs)
run_contractiq_lan.bat   :: same, but also reachable from other devices on your network
run_contractiq.bat       :: dev mode: Vite dev server :5173 + backend (hot reload)
run_backend.bat          :: backend only
run_frontend.bat         :: frontend dev server only
```

The production launchers serve the built frontend (`frontend/dist/`) directly from
FastAPI — one process, one port, no Node needed at runtime. The default port is
**8010**; override with `set BACKEND_PORT=<port>` before launching. After changing
frontend code, rebuild with `cd frontend && npm run build`. See `docs/DEPLOYMENT.md`.

## GPU support

At startup the app checks `torch.cuda.is_available()`. With an NVIDIA GPU and the CUDA
PyTorch build installed, inference runs on the GPU automatically. On a CPU-only laptop the
same code falls back to CPU — no source edits. `setup_windows.bat` detects NVIDIA hardware
(`nvidia-smi`) and offers the correct official PyTorch build. If the installed NVIDIA
driver is too old for the CUDA build (e.g. driver predates the CUDA runtime), the app
detects this and falls back to CPU safely instead of crashing.

## CPU support

CPU-only machines are fully supported: the model runs on CPU with the
retrieval-optimized pipeline (~80 s median contract; GPU ≈ 4–12 s).

## Project structure

```
backend/    FastAPI app, parser, risk engine, DB (backend/app/…)
frontend/   React + TS + Vite app (frontend/src/…)
ml/         configs, inference/train/evaluate code, bundled model (ml/models/final)
data/       CUAD dataset (data.zip → data/raw), training features (development assets)
storage/    uploads, temp, contractiq.db (created at runtime)
docs/       user guide, architecture, ML, risk, security, troubleshooting
reports/    per-phase reports and QA evidence
```

## Testing

```bat
.venv\Scripts\activate
python -m pytest backend\tests ml\tests -q
cd frontend && npm run test && npm run lint && npm run build
```

## Security / privacy

Uploads never leave your machine and are never executed. See `docs/SECURITY.md`
(file validation, path-traversal protection, raw-text retention, log privacy).

**LAN mode caveat:** `run_contractiq_lan.bat` serves the app to every device on your
network, and the app has no authentication — use it on a trusted Wi-Fi only, and
prefer `run_contractiq_prod.bat` (localhost only) otherwise. Windows Firewall will
ask for permission the first time another device connects.

## Limitations

Single-user local app (no auth); synchronous analysis; risk rules are heuristics;
scanned PDFs need OCR (not implemented). Full list: `reports/phase8_final_qa.md`.

## Legal disclaimer

ContractIQ provides AI-assisted contract analysis and is not a substitute for
professional legal advice. Results should be reviewed by a qualified professional.

## License

This project currently has **no explicit redistribution license** — all rights reserved
by the author until one is chosen. Third-party components keep their own licenses
(see `THIRD_PARTY_NOTICES.md`).

## Model attribution

Fine-tuned from [`deepset/minilm-uncased-squad2`](https://huggingface.co/deepset/minilm-uncased-squad2)
(**CC-BY-4.0**, bundled in `ml/models/final` with attribution) on the
[CUAD v1](https://www.atticusprojectai.org/cuad) dataset. Details: `docs/ML_MODEL.md`.
