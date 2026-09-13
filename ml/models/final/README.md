# ml/models/final

The fine-tuned ContractIQ QA model lives here when present
(`model.safetensors` ~127 MB + config + tokenizer). The weights file is
**intentionally not stored in the git repository** — it exceeds GitHub's
100 MB per-file limit and the repo is intentionally kept free of large files.

## How to get the model

1. **Recommended:** download `model.safetensors` from the project's
   GitHub **Releases** page (attached as a release asset) and place it in
   this folder, **or**
2. transfer it directly from a machine that has the project
   (see `TRANSFER_TO_ANOTHER_LAPTOP.md`), **or**
3. use Git LFS if the repository owner enables it
   (see `docs/DEPLOYMENT.md`).

## What happens without it

The app still runs: at startup `ml/src/inference.py` detects that the
fine-tuned checkpoint is missing and falls back to the public baseline
`deepset/minilm-uncased-squad2` (downloaded once from Hugging Face).
The UI reports the model state honestly as `zero_shot_baseline` instead of
`fine_tuned` — extraction quality is noticeably lower, but every other
feature (evidence offsets, risk engine, history) works unchanged.
