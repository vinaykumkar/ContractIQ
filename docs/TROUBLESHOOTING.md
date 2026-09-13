# ContractIQ — Troubleshooting

Practical fixes for the most common problems.

## Setup problems

**"Python was not found on PATH"**
Install Python 3.11–3.13 from https://www.python.org/downloads/ and tick
*"Add python.exe to PATH"*. Re-run `setup_windows.bat`.

**"Python X.Y is not supported"**
The project is tested on Python 3.11 (supported 3.11–3.13). Install a
supported version — you can keep other versions installed side by side.

**"Node.js was not found on PATH"**
Install Node.js 20+ (LTS) from https://nodejs.org/ and re-run
`setup_windows.bat`. The backend works without Node; only the frontend needs it.

**PyTorch install fails**
`setup_windows.bat` falls back to the CPU build automatically. For manual
CUDA setup use the official index only:
`pip install torch==2.13.0+cu130 --index-url https://download.pytorch.org/whl/cu130`

## Runtime problems

**"ContractIQ Engine Offline"**
The backend isn't running. Start `run_contractiq_prod.bat` (or `run_backend.bat`),
then click **Retry now** in the banner. The backend can take ~10 s to start.

**Port already in use / the app was running but "disappeared"**
Close the other application using the port, or pick another one: set
`set BACKEND_PORT=8011` before starting (the production UI uses same-origin
`/api`, so no frontend change is needed). Note for the original development
machine: another project on it starts servers on ports 8000/8002 — the
production launchers therefore default to **8010**.

**The first analysis after starting the backend is slow (up to ~30 s)**
The ML model loads on the first analysis, not at startup. Later analyses are
much faster.

**"The analysis model is not available" (503)**
The model files are missing. Check that `ml/models/final/model.safetensors`
exists, then run `python scripts\verify_install.py`. Without the bundled model
the app tries the pretrained baseline (downloads once from Hugging Face).

**Analysis is slow**
CPU-only machines take ~1–2 minutes for a typical contract. An NVIDIA GPU
with the CUDA PyTorch build reduces this to seconds. Close other GPU-heavy
applications while analyzing.

**CUDA errors / GPU out of memory**
The analysis is marked FAILED with a "GPU memory exhausted" message and the
server keeps running. Try a shorter document, or switch to CPU by temporarily
editing `.env` — or simply retry (the CUDA cache is cleared automatically).

**NVIDIA driver older than the installed CUDA build**
Symptom (before v0.5.1): the first analysis crashed the backend with no
traceback (access violation in torch CUDA stream checks). Current code detects
this at startup and runs on CPU with eager attention instead — no crash. To
regain GPU speed, update the NVIDIA driver to one matching the CUDA build
(see the `pip install torch==2.13.0+cu130` note above).

## Document problems

**"No usable text layer — OCR required"**
The PDF is a scan/image. ContractIQ does not fabricate text — run OCR
externally and upload the text-based result.

**"Password-protected / encrypted document"**
Remove the PDF password before uploading.

**"The document appears to be corrupt"**
The file is damaged or not the format its extension claims. Re-save or
re-export the file.

**Very long contracts**
Contracts of 200k+ characters work, but analysis takes longer. Everything
else in the UI stays responsive.

## Still stuck?

Run `python scripts\system_check.py` and `python scripts\verify_install.py`
and compare against the expected output in the README.
