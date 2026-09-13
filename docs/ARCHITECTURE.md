# ContractIQ — Architecture

```
┌─────────────────────────────┐
│ React + TypeScript + Vite   │  frontend/src
│ pages, Risk Orb, Clause Map │
└──────────────┬──────────────┘
               │ HTTP /api  (fetch, structured error envelope)
┌──────────────▼──────────────┐
│ FastAPI  (backend/app)      │  routes, schemas, request-IDs, CORS
│  api/routes/…               │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Services                    │
│  document_parser.py         │  PDF (PyMuPDF) / DOCX (python-docx) / TXT
│  contract_analysis.py       │  orchestration + transactions
│  ml_adapter.py              │  stable analyzer interface
└──────┬───────────────┬──────┘
       │               │
┌──────▼──────┐  ┌─────▼──────────────┐
│ ML layer    │  │ Risk engine        │
│ (ml/src)    │  │ (backend/app/risk) │
│ Contract-   │  │ transparent rules  │
│ Analyzer    │  │ 0–100, 3 bands     │
└──────┬──────┘  └─────┬──────────────┘
       │               │
┌──────▼───────────────▼──────┐
│ SQLAlchemy  →  SQLite       │  contracts, analyses, clause_results,
│ (backend/app/db)            │  risk_findings
└─────────────────────────────┘
```

## Serving the built frontend (production mode)

When `frontend/dist/` exists (built with `npm run build`), `app/main.py` mounts
it into the same FastAPI process: `/assets/*` is served statically and every
non-`/api` GET falls back to `index.html`, so SPA deep links (`/contracts/<id>`)
resolve on a single port (default **8010** via the `run_contractiq_prod.bat` /
`run_contractiq_lan.bat` launchers). The production frontend calls the API with a
same-origin base (`/api`), so the served app works on any host/port without
rebuilding; unknown `/api` paths still return 404 JSON, never HTML. In dev mode
(`run_frontend.bat`, port 5173) Vite serves the UI instead and the client targets
`http://127.0.0.1:8000/api`.

## Request flow (analyze)

1. `POST /api/contracts/upload` → file validated (extension/size/filename) →
   stored as `storage/uploads/<uuid>.<ext>` → parsed into `ParsedDocument` →
   sha-256 of normalized text → `Contract` row (`READY`).
2. `POST /api/contracts/{id}/analyze` → service marks `ANALYZING` →
   `ContractAnalyzer.analyze_contract(text)` runs the 15 enabled clause
   questions → per-clause best span + CLS no-answer score →
   `evaluate_risk()` applies heuristic rules → results persisted atomically
   (`COMPLETED`) or `FAILED` with a concise message.

## Model singleton & device selection

- `MLAnalyzerAdapter` creates **one** `ContractAnalyzer` per backend process;
  the transformer loads lazily on the first analysis and stays on its device.
- `ml/src/device.py::get_device()` returns `cuda` when available, else `cpu` —
  nothing hard-codes a GPU id or CUDA path.

## Inference internals

- Each contract's text is tokenized **once** (char offsets preserved); clause
  questions are assembled as `[CLS] question [SEP] context-window [SEP]`
  windows (512 tokens, 128 stride; retrieval narrows 11 of 15 clauses to the
  TF-IDF top-15 blocks).
- The decoder scores every valid `(start, end)` span, compares against the
  `[CLS]` no-answer score, and maps the winning tokens back to **exact
  character offsets** in the original text (invariant tested end-to-end).

## Evidence offsets

Offsets always index the text served by `GET /api/contracts/{id}/text`.
`clause_results.start_char/end_char` → verified in Phase 8 across all stored
analyses: 0 mismatches.

## Risk heuristics

`backend/app/risk/rules.py` defines 15 transparent rules (presence, absence,
wording regex; weight 0–18). `evaluate_risk()` is deterministic, excludes
low-confidence findings from the score, and bands 0–30 LOW / 31–60 MEDIUM /
61–100 HIGH. See `docs/RISK_SCORING.md`.

## Database

Four tables (`contracts → analyses → clause_results, risk_findings`) with
cascade deletes; transactions via `session_scope` (rollback on error); stale
`ANALYZING` rows recovered at startup; SQLite default at
`storage/contractiq.db`, any SQLAlchemy URL via `CONTRACTIQ_DB_URL`.
