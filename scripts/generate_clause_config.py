#!/usr/bin/env python
"""Generate the ContractIQ clause registry from CUAD question templates.

Reads the actual question templates from:
    data/raw/CUADv1.json

The generated registry contains all 41 CUAD categories while enabling
the 15 Version-1 clauses.

Usage:
    python scripts/generate_clause_config.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CUAD_SOURCE = (
    PROJECT_ROOT / "data" / "raw" / "CUADv1.json"
)

CLAUSE_CONFIG_PATH = (
    PROJECT_ROOT / "ml" / "configs" / "clauses.json"
)


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


CATEGORY_PATTERN = re.compile(
    r'related to "(.+?)" that should be reviewed'
)


def load_cuad_data() -> dict:
    """Load the CUAD dataset from disk."""
    with CUAD_SOURCE.open(
        "r",
        encoding="utf-8",
    ) as source_file:
        return json.load(source_file)


def extract_questions(dataset: dict) -> dict[str, str]:
    """Extract one question template for every CUAD category."""
    category_questions: dict[str, str] = {}

    for document in dataset["data"]:
        paragraphs = document["paragraphs"]

        for paragraph in paragraphs:
            for qa in paragraph["qas"]:
                question = qa.get("question", "")

                match = CATEGORY_PATTERN.search(question)

                if match:
                    category = match.group(1)

                    category_questions.setdefault(
                        category,
                        question,
                    )

    return category_questions


def validate_categories(
    questions: dict[str, str],
) -> bool:
    """Ensure the dataset contains all expected CUAD categories."""
    if len(questions) != 41:
        print(
            f"FATAL: expected 41 categories, "
            f"found {len(questions)}",
            file=sys.stderr,
        )
        return False

    missing_categories = [
        category
        for category in V1_LABELS
        if category not in questions
    ]

    if missing_categories:
        print(
            "FATAL: V1 clauses not found in dataset: "
            f"{missing_categories}",
            file=sys.stderr,
        )
        return False

    return True


def build_clause_registry(
    questions: dict[str, str],
) -> list[dict]:
    """Build the complete clause configuration list."""
    registry = []

    for category in sorted(questions):
        registry.append(
            {
                "label": V1_LABELS.get(category, ""),
                "cuad_category": category,
                "enabled": category in V1_LABELS,
                "question": questions[category],
            }
        )

    return registry


def build_config(clauses: list[dict]) -> dict:
    """Create the complete ContractIQ configuration."""
    enabled_count = sum(
        1
        for clause in clauses
        if clause["enabled"]
    )

    return {
        "_meta": {
            "description": (
                "ContractIQ central clause registry. Generated from "
                "the actual CUAD question templates in "
                "data/raw/CUADv1.json "
                "(see scripts/generate_clause_config.py). "
                "To enable a new clause later, set "
                "\"enabled\": true and assign a stable \"label\"."
            ),
            "dataset": "CUAD v1 (Henriksson et al., 2021)",
            "generated_at": "2026-08-30",
            "n_categories_total": len(clauses),
            "n_enabled_v1": enabled_count,
            "disclaimer": (
                "AI-assisted analysis. Results should be reviewed "
                "by a qualified professional."
            ),
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
            "note": (
                "0-30 LOW, 31-60 MEDIUM, 61-100 HIGH "
                "(configurable; heuristic engine only)."
            ),
        },
        "clauses": clauses,
    }


def write_config(config: dict) -> None:
    """Write the generated configuration to disk."""
    CLAUSE_CONFIG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CLAUSE_CONFIG_PATH.write_text(
        json.dumps(
            config,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> int:
    """Generate and save the ContractIQ clause configuration."""
    if not CUAD_SOURCE.exists():
        print(
            "ERROR: data/raw/CUADv1.json not found. "
            "Extract data.zip first.",
            file=sys.stderr,
        )
        return 1

    dataset = load_cuad_data()
    questions = extract_questions(dataset)

    if not validate_categories(questions):
        return 1

    clauses = build_clause_registry(questions)
    config = build_config(clauses)

    write_config(config)

    print(f"Wrote {CLAUSE_CONFIG_PATH}")
    print(
        "Enabled clauses: "
        f"{config['_meta']['n_enabled_v1']} / "
        f"{config['_meta']['n_categories_total']}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
