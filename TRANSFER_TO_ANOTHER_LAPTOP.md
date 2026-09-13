# Transferring ContractIQ to Another Laptop

Simple, step-by-step. Total time: ~15 minutes (most of it waiting for installs).

## STEP 1 — Copy the folder

Copy the **entire** ContractIQ folder to the new laptop (USB drive, zip, or any
network transfer). Any location works — `D:\Projects\ContractIQ`,
`C:\Users\You\Desktop\ContractIQ`, a path with spaces, etc.

You do **NOT** need to copy (setup recreates them, and they may not work on
the new machine):

- `.venv\` (the Python virtual environment)
- `frontend\node_modules\`
- `__pycache__`, `.pytest_cache`, caches
- Hugging Face / pip / npm caches

You **DO** need: everything else — especially `ml\models\final\` (the AI
model), `backend\`, `frontend\`, `ml\`, `storage\` (optional, keeps history).

## STEP 2 — Install prerequisites (one-time)

1. **Python 3.11 – 3.13** — https://www.python.org/downloads/
   (tick *"Add python.exe to PATH"*)
2. **Node.js 20+ (LTS)** — https://nodejs.org/
3. Optional: NVIDIA GPU driver if the laptop has an NVIDIA GPU.

No CUDA Toolkit, no Git, no paid software required.

## STEP 3 — Run setup

Double-click **`setup_windows.bat`**. It will:

- check Python and Node versions,
- create a fresh `.venv` inside the copied folder,
- install all Python dependencies (asks whether to install the CUDA PyTorch
  build when it detects an NVIDIA GPU),
- install frontend dependencies from the lockfile,
- create `storage\` folders, `.env`, initialize the database,
- verify the bundled model and imports.

Wait until it prints *"setup finished successfully"*.

## STEP 4 — Run

One-time: build the production UI — `cd frontend && npm run build` (Node is only
needed for this build step, not to run the app afterwards).

Double-click **`run_contractiq_prod.bat`**. One window opens serving the app and
API together; after a few seconds your browser opens **http://127.0.0.1:8010**.

Variants: **`run_contractiq_lan.bat`** also lets other devices on your Wi-Fi open
the app via this PC's IP; **`run_contractiq.bat`** starts the dev-server mode
(two windows, hot reload, http://localhost:5173).

## STEP 5 — Use it

Upload a contract on the **New Analysis** page, press analyze, and explore the
intelligence report. See `docs\USER_GUIDE.md` for the full walkthrough.

## Notes

- **GPU vs CPU:** automatic. With an NVIDIA GPU + CUDA PyTorch build the model
  runs on the GPU (seconds per contract); otherwise CPU (up to ~1–2 minutes).
- **Your data stays on the laptop** — nothing is uploaded to any cloud service.
- **Existing history transfers too** if you copied `storage\contractiq.db`
  (skip copying that file if you prefer a fresh, empty database).
- **Model independence:** the app loads the bundled `ml\models\final\` model —
  the original laptop's Hugging Face cache is not needed.
- If setup fails, read the message in the console window (it names the missing
  prerequisite), fix it, and re-run. `docs\TROUBLESHOOTING.md` covers the
  common cases.
