# ContractIQ User Guide

A simple, step-by-step guide to using ContractIQ.

## 1. Start the project

Double-click **`run_contractiq_prod.bat`**. One window opens (it serves both the
app and the API) — leave it open. Your browser opens at `http://127.0.0.1:8010`.
If it doesn't, open that address manually.

To also let other devices on your Wi-Fi use the app, start
**`run_contractiq_lan.bat`** instead and share `http://<this-PC-ip>:8010`
(check your IP with `ipconfig`).

If you see *"ContractIQ is not installed on this machine"*, run
**`setup_windows.bat`** first (see `TRANSFER_TO_ANOTHER_LAPTOP.md`).

## 2. Upload a contract

Go to **New Analysis** and either drag a file onto the circle or click it to
browse. Supported formats: **PDF, DOCX, TXT** (up to 20 MB by default).

## 3. Supported formats

- **PDF** — text-based PDFs work best
- **DOCX** — Word documents (paragraphs and tables)
- **TXT** — plain text files

Scanned/image-only PDFs are rejected with a clear "OCR required" message —
ContractIQ never guesses text it cannot read.

## 4. Analyze

After upload, press the analyze button (or it starts automatically on the
upload page). The engine reads the document, finds each enabled clause, and
scores risk patterns. This takes a few seconds on a GPU, up to a couple of
minutes on CPU for long contracts. The animated stages show what is happening —
they are a process overview, not an exact percentage.

## 5. Understand the Risk Orb

The large circular gauge in the intelligence rail shows the overall risk:

- **Score (0–100)** — how many risk rules fired, weighted by importance
- **Level** — LOW (0–30), MEDIUM (31–60), HIGH (61–100)
- **Findings** — how many rules were triggered

This score comes from transparent keyword/presence rules — **not** from the AI
model — and is not legal advice.

## 6. Use the Clause Intelligence Map

The circular map shows your contract in the middle and one node per clause.
Bright nodes = clauses found; dim nodes = not found; colors hint at risk.
While analyzing, connections pulse.

## 7. Click a clause

Click any clause node or clause card. The document on the left automatically
scrolls to the clause and highlights the exact words the engine extracted.

## 8. Evidence highlighting

The bright highlighted text is the **exact evidence** — the same characters the
model returned, taken straight from your document. Other found clauses stay
lightly marked so you can see the whole document at a glance. Use
**"Copy evidence"** on a clause card to copy the passage.

## 9. History

Open **Contracts** to see everything you have analyzed. Use the search box,
status chips and risk filter to find documents. Click any entry to reopen its
full intelligence report — previous analyses restore instantly without
re-running the model.

## 10. Delete a contract

Hover over a row in Contracts and click the trash icon. The contract, its
analysis, and its stored file are removed.

## 11. Common errors

| Message | What it means |
|---|---|
| ContractIQ Engine Offline | The backend isn't running — start `run_contractiq_prod.bat` (or `run_backend.bat`), then click "Retry now" |
| Unsupported file type | Only PDF/DOCX/TXT can be uploaded |
| The document appears to be corrupt | The file is damaged — try re-exporting it |
| Password-protected / encrypted | Encrypted PDFs can't be read — remove the password first |
| OCR required | Scanned/image-only PDF has no text layer |
| The analysis model is not available | The model files are missing — see `docs/TROUBLESHOOTING.md` |
| Analysis in progress | An analysis for this contract is already running |

More help: `docs/TROUBLESHOOTING.md`.
