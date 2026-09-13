#!/usr/bin/env python
"""Generate ml/configs/clauses.json from the actual CUAD question templates.

Extracts the exact question text for all 41 categories from
data/raw/CUADv1.json and marks the 15 Version-1 clauses as enabled.
Re-run any time the registry needs regeneration:

    python scripts/generate_clause_config.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CUAD = PROJECT_ROOT / "data" / "raw" / "CUADv1.json"
OUT_PATH = PROJECT_ROOT / "ml" / "configs" / "clauses.json"

V1_LABELS = {
    "Document Name": "document_name",
    "Parties": "parties",
    "Agreement Date": "agreement_date",
    "Effective Date": "effective_date",
    "Expiration Date": "expiration_date",
    "Renewal Term": "renewal_term",
    "Governing Law": "governing_law",
    "Termination For Convenience": "termination_for_convenience",
    "Non-Compete": "non_compete",
    "Exclusivity": "exclusivity",
    "Anti-Assignment": "anti_assignment",
    "License Grant": "license_grant",
    "Audit Rights": "audit_rights",
    "Cap On Liability": "cap_on_liability",
    "Insurance": "insurance",
}

CATEGORY_RE = re.compile(r'related to "(.+?)" that should be reviewed')


def main() -> int:
    if not RAW_CUAD.exists():
        print("ERROR: data/raw/CUADv1.json not found. Extract data.zip first.", file=sys.stderr)
        return 1

    with RAW_CUAD.open("r", encoding="utf-8") as f:
        data = json.load(f)

    questions: dict[str, str] = {}
    for item in data["data"]:
        for qa in item["paragraphs"][0]["qas"]:
            m = CATEGORY_RE.search(qa.get("question", ""))
            if m:
                questions.setdefault(m.group(1), qa["question"])

    if len(questions) != 41:
        print(f"FATAL: expected 41 categories, found {len(questions)}", file=sys.stderr)
        return 1

    missing = [c for c in V1_LABELS if c not in questions]
    if missing:
        print(f"FATAL: V1 clauses not found in dataset: {missing}", file=sys.stderr)
        return 1

    clauses = [{
        "label": V1_LABELS.get(cat, ""),
        "cuad_category": cat,
        "enabled": cat in V1_LABELS,
        "question": questions[cat],
    } for cat in sorted(questions)]

    config = {
        "_meta": {
            "description": "ContractIQ central clause registry. Generated from the actual "
                           "CUAD question templates in data/raw/CUADv1.json "
                           "(see scripts/generate_clause_config.py). To enable a new clause "
                           "later, set \"enabled\": true and assign a stable \"label\".",
            "dataset": "CUAD v1 (Henriksson et al., 2021)",
            "generated_at": "2026-08-30",
            "n_categories_total": len(clauses),
            "n_enabled_v1": sum(1 for c in clauses if c["enabled"]),
            "disclaimer": "AI-assisted analysis. Results should be reviewed by a qualified professional.",
        },
        "inference": {
            "max_seq_len": 512,
            "doc_stride": 128,
            "max_answer_tokens": 64,
            "no_answer_threshold": 0.35,
            "min_confidence": 0.25,
        },
        "risk_bands": {
            "low_max": 30,
            "medium_max": 60,
            "note": "0-30 LOW, 31-60 MEDIUM, 61-100 HIGH (configurable; heuristic engine only).",
        },
        "clauses": clauses,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    print(f"Enabled clauses: {config['_meta']['n_enabled_v1']} / {config['_meta']['n_categories_total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
