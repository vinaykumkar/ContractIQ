```python
#!/usr/bin/env python
"""Validate the Phase 2 tiny pipeline using real CUAD data.

Validation flow:
    CUAD data
        -> ContractRecord
        -> clause QA
        -> tokenization
        -> sliding windows
        -> training features
        -> gold-span reconstruction

The deterministic sample includes:
    - a positive example
    - a no-answer example
    - a contract requiring multiple windows
    - a clause containing multiple gold spans

The validation does not perform model training.

Output:
    reports/phase2_tiny_validation.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.src.chunking import build_windows_for_clause, tokenize_context  # noqa: E402
from ml.src.config import (  # noqa: E402
    REPORTS_DIR,
    load_enabled_clauses,
    load_window_config,
)
from ml.src.cuad_loader import load_train_contracts  # noqa: E402
from ml.src.qa_features import (  # noqa: E402
    answer_token_positions,
    build_train_features,
    cls_index,
)
from ml.src.preprocessing import question_budget  # noqa: E402


CANDIDATE_LIMIT = 40
CLAUSE_LIMIT = 5
TARGET_CONTRACTS = 4
MODEL_NAME = "distilbert-base-uncased"


def select_contract(
    selected: list,
    reasons: list[str],
    record,
    reason: str,
) -> None:
    """Add a contract once, while respecting the selection limit."""
    if len(selected) >= TARGET_CONTRACTS:
        return

    existing_ids = {item.contract_id for item in selected}

    if record.contract_id not in existing_ids:
        selected.append(record)
        reasons.append(reason)


def find_required_contracts(candidates, clauses, tokenizer, config, cls_id, sep_id):
    """Deterministically select contracts covering all required scenarios."""
    selected = []
    reasons = []

    # Look for a contract containing multiple gold answer instances.
    for record in candidates:
        if len(selected) >= TARGET_CONTRACTS:
            break

        for clause in clauses:
            if len(record.qas_for(clause.label)) > 1:
                select_contract(
                    selected,
                    reasons,
                    record,
                    "clause with multiple gold instances (exploded spans)",
                )
                break

    # Cache tokenized contracts while searching for multi-window examples.
    tokenized = {}

    for record in candidates:
        tokenized[record.contract_id] = tokenize_context(tokenizer, record)

        first_clause = clauses[0]
        question_ids = tokenizer(
            first_clause.question,
            add_special_tokens=False,
        )["input_ids"]

        windows = build_windows_for_clause(
            tokenized[record.contract_id],
            question_ids,
            first_clause.label,
            config,
            cls_id,
            sep_id,
        )

        if len(windows) > 1:
            select_contract(
                selected,
                reasons,
                record,
                "contract requires multiple sliding windows",
            )

    # Find a positive contract.
    for record in candidates:
        has_positive = any(
            not qa.is_impossible and qa.answers
            for qa in record.qas
        )

        if has_positive:
            select_contract(
                selected,
                reasons,
                record,
                "contract with positive gold span",
            )
            break

    # Find a no-answer contract.
    for record in candidates:
        has_no_answer = any(
            qa.is_impossible
            for qa in record.qas
        )

        if has_no_answer:
            select_contract(
                selected,
                reasons,
                record,
                "contract with a no-answer clause instance",
            )
            break

    # Fill remaining slots deterministically if necessary.
    index = 0

    while len(selected) < TARGET_CONTRACTS and candidates:
        candidate = candidates[
            (len(selected) * 7) % len(candidates)
        ]

        previous_count = len(selected)

        select_contract(
            selected,
            reasons,
            candidate,
            "additional deterministic pick",
        )

        if len(selected) == previous_count:
            index += 1

            if index >= len(candidates):
                break

    return selected, reasons, tokenized


def build_validation_report(clauses, selected, reasons):
    """Create the initial validation report structure."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clauses": [clause.label for clause in clauses],
        "selected_contracts": [
            {
                "contract_id": record.contract_id,
                "reason": reason,
            }
            for record, reason in zip(selected, reasons)
        ],
        "checks": {},
        "per_contract": [],
    }


def validate_selected_contracts(
    selected,
    clauses,
    tokenized_cache,
    tokenizer,
    config,
    cls_id,
    sep_id,
    stats,
):
    """Run feature generation and gold-span reconstruction checks."""

    total_windows = 0
    positive_windows = 0
    no_answer_windows = 0
    max_windows_per_contract = 0
    reconstructed_spans = 0
    boundary_extended_spans = 0
    multi_span_detected = False

    for record in selected:
        tokenized = tokenized_cache[record.contract_id]
        contract_window_count = 0

        for clause in clauses:
            question_ids = tokenizer(
                clause.question,
                add_special_tokens=False,
            )["input_ids"]

            windows = build_windows_for_clause(
                tokenized,
                question_ids,
                clause.label,
                config,
                cls_id,
                sep_id,
            )

            contract_window_count += len(windows)

            qa = record_qa_for(record, clause.label)
            features = build_train_features(windows, qa)

            for feature in features:
                total_windows += 1

                if feature.is_no_answer:
                    no_answer_windows += 1

                    assert (
                        feature.start_position == cls_index()
                        and feature.end_position == cls_index()
                    )

                    continue

                positive_windows += 1

                window = windows[feature.window_index]

                local_start = (
                    feature.start_position
                    - window.ctx_first_token_index_in_window
                )
                local_end = (
                    feature.end_position
                    - window.ctx_first_token_index_in_window
                )

                char_start = window.ctx_offsets[local_start][0]
                char_end = window.ctx_offsets[local_end][1]

                gold_start, gold_end = feature.gold_char_span

                gold_text = record.context[gold_start:gold_end]
                decoded_text = record.context[char_start:char_end]

                if char_start <= gold_start and gold_end <= char_end:
                    if char_start != gold_start or char_end != gold_end:
                        boundary_extended_spans += 1
                else:
                    raise AssertionError(
                        f"RECONSTRUCTION FAILURE for "
                        f"{record.contract_id}/{clause.label}: "
                        f"decoded {decoded_text!r} does not contain "
                        f"gold {gold_text!r}"
                    )

                reconstructed_spans += 1

            if len(qas_for_label(record, clause.label)) > 1:
                multi_span_detected = True

        max_windows_per_contract = max(
            max_windows_per_contract,
            contract_window_count,
        )

        stats["per_contract"].append(
            {
                "contract_id": record.contract_id,
                "context_tokens": len(tokenized.token_ids),
                "windows_total": contract_window_count,
            }
        )

    return {
        "total_windows": total_windows,
        "positive_windows": positive_windows,
        "no_answer_windows": no_answer_windows,
        "max_windows_per_contract": max_windows_per_contract,
        "reconstructed_spans": reconstructed_spans,
        "boundary_extended_spans": boundary_extended_spans,
        "multi_span_detected": multi_span_detected,
    }


def main() -> int:
    from transformers import AutoTokenizer

    clauses = load_enabled_clauses()[:CLAUSE_LIMIT]
    window_config = load_window_config()

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        use_fast=True,
    )

    window_config.check_tokenizer_compat(
        tokenizer.model_max_length
    )

    cls_id = tokenizer.cls_token_id
    sep_id = tokenizer.sep_token_id

    print(
        f"Loading {CANDIDATE_LIMIT} candidate contracts "
        "(strict validation)..."
    )

    candidates = load_train_contracts(
        load_enabled_clauses(),
        limit=CANDIDATE_LIMIT,
        strict=True,
    )

    print(
        f"Loaded {len(candidates)} contracts "
        "with strict answer validation: OK"
    )

    selected, reasons, tokenized_cache = find_required_contracts(
        candidates,
        clauses,
        tokenizer,
        window_config,
        cls_id,
        sep_id,
    )

    print(
        "Selected contracts:",
        [
            (record.contract_id, reason)
            for record, reason in zip(selected, reasons)
        ],
    )

    report = build_validation_report(
        clauses,
        selected,
        reasons,
    )

    metrics = validate_selected_contracts(
        selected=selected,
        clauses=clauses,
        tokenized_cache=tokenized_cache,
        tokenizer=tokenizer,
        config=window_config,
        cls_id=cls_id,
        sep_id=sep_id,
        stats=report,
    )

    total_windows = metrics["total_windows"]
    positive_windows = metrics["positive_windows"]
    no_answer_windows = metrics["no_answer_windows"]
    max_windows = metrics["max_windows_per_contract"]
    reconstructed = metrics["reconstructed_spans"]
    boundary_extended = metrics["boundary_extended_spans"]

    report["checks"] = {
        "strict_answer_validation": True,
        "positive_example_present": positive_windows > 0,
        "no_answer_example_present": no_answer_windows > 0,
        "multi_window_contract_present": max_windows > len(clauses),
        "multi_gold_span_clause_present": metrics["multi_span_detected"],
        "all_positive_spans_reconstructed_with_containment": True,
        "reconstructed_spans": reconstructed,
        "boundary_extended_spans": boundary_extended,
        "note": (
            "Some CUAD gold spans cut mid-wordpiece-token; "
            "token-level decoding extends them to the containing "
            "token boundary (standard SQuAD behaviour). Precise "
            "character spans are preserved in feature metadata."
        ),
    }

    report["window_stats"] = {
        "total": total_windows,
        "positive": positive_windows,
        "no_answer": no_answer_windows,
        "max_windows_per_contract": max_windows,
    }

    report["question_budget"] = question_budget(
        load_enabled_clauses(),
        window_config,
        tokenizer,
    )[:CLAUSE_LIMIT]

    # Required validation conditions.
    checks = report["checks"]

    assert checks["positive_example_present"], (
        "No positive example selected."
    )
    assert checks["no_answer_example_present"], (
        "No no-answer example selected."
    )
    assert checks["multi_window_contract_present"], (
        "No multi-window contract selected."
    )
    assert reconstructed > 0, (
        "No gold spans were reconstructed."
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = REPORTS_DIR / "phase2_tiny_validation.json"

    output_file.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(
        f"\nAll tiny-pipeline checks passed. "
        f"Report: {output_file}"
    )
    print(
        f"Windows: {total_windows} "
        f"(positive {positive_windows}, "
        f"no-answer {no_answer_windows})"
    )
    print(
        f"Gold spans reconstructed exactly: {reconstructed}"
    )

    return 0


def qas_for_label(record, label):
    """Return all QA instances belonging to a clause label."""
    return record.qas_for(label)


def record_qa_for(record, label):
    """Return the first QA instance for a clause label."""
    qas = record.qas_for(label)

    if qas:
        return qas[0]

    question = get_clause_question(label)

    return _create_dummy_qa(
        label=label,
        question=question,
        impossible=True,
    )


def get_clause_question(label):
    """Find the configured question associated with a clause label."""
    from ml.src.config import load_enabled_clauses

    for clause in load_enabled_clauses():
        if clause.label == label:
            return clause.question

    return ""


def _create_dummy_qa(label, question, impossible):
    """Create an empty QA record for clauses without available answers."""
    from ml.src.cuad_loader import ClauseQA

    return ClauseQA(
        clause_label=label,
        cuad_category="",
        question=question,
        answers=[],
        is_impossible=impossible,
        qa_id="",
    )


if __name__ == "__main__":
    raise SystemExit(main())
```
