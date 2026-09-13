"""Load CUAD JSON files into typed contract records with strict answer validation.

The raw files are SQuAD-style dicts; downstream code works exclusively with
the dataclasses here so the nested-JSON shape stays contained in one module.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    TEST_PATH,
    TRAIN_SEPARATE_PATH,
    CUADV1_PATH,
    ClauseSpec,
    ConfigError,
)

CATEGORY_RE = re.compile(r'related to "(.+?)" that should be reviewed')


class CuadDataError(RuntimeError):
    """Raised when the dataset violates a structural invariant.

    We never silently repair malformed records: Phase 1 measured zero
    anomalies, so any new mismatch indicates corrupted preprocessing/data.
    """


@dataclass(frozen=True)
class AnswerSpan:
    """A gold answer span as character offsets into the contract context."""

    text: str
    start: int

    @property
    def end(self) -> int:
        return self.start + len(self.text)


@dataclass
class ClauseQA:
    """One (contract, clause) question-answering instance."""

    clause_label: str  # e.g. "governing_law"; empty string if clause not enabled
    cuad_category: str  # e.g. "Governing Law" (actual CUAD name)
    question: str  # canonical CUAD question for the category
    answers: list[AnswerSpan] = field(default_factory=list)
    is_impossible: bool = False
    qa_id: str = ""


@dataclass
class ContractRecord:
    """One contract with its clause QA instances."""

    contract_id: str  # CUAD title (unique across the dataset)
    context: str
    qas: list[ClauseQA] = field(default_factory=list)
    split: str = ""  # "", "train", "val", or "test" (assigned by preprocessing)

    def qas_for(self, clause_label: str) -> list[ClauseQA]:
        return [qa for qa in self.qas if qa.clause_label == clause_label]


def validate_answer(context: str, answer: AnswerSpan, contract_id: str, qa_id: str) -> None:
    """Verify the gold span is an exact substring at the recorded offset.

    Phase 1 measured zero mismatches across 65,940 answers; any mismatch is
    treated as data corruption and stops the pipeline (fail loudly, never
    silently repair).
    """
    if answer.start < 0:
        raise CuadDataError(
            f"Negative answer_start in contract '{contract_id}' qa '{qa_id}': {answer.start}"
        )
    if answer.end > len(context):
        raise CuadDataError(
            f"Answer out of bounds in contract '{contract_id}' qa '{qa_id}': "
            f"[{answer.start}:{answer.end}] > context length {len(context)}"
        )
    if context[answer.start : answer.end] != answer.text:
        raise CuadDataError(
            f"Answer text mismatch in contract '{contract_id}' qa '{qa_id}': "
            f"recorded {answer.text!r} but context slice is "
            f"{context[answer.start : answer.end]!r}"
        )


def _parse_qa(
    qa: dict,
    category: str,
    question: str,
    label_for_category: dict[str, str],
    contract_id: str,
    context: str,
    strict: bool,
) -> ClauseQA | None:
    qa_id = qa.get("id", "")
    impossible = bool(qa.get("is_impossible", False))
    raw_answers = qa.get("answers") or []
    if impossible and raw_answers:
        raise CuadDataError(
            f"is_impossible=True but {len(raw_answers)} answers present "
            f"in contract '{contract_id}' qa '{qa_id}'"
        )
    answers = [
        AnswerSpan(text=a["text"], start=int(a["answer_start"])) for a in raw_answers
    ]
    if strict:
        for a in answers:
            validate_answer(context, a, contract_id, qa_id)
    return ClauseQA(
        clause_label=label_for_category.get(category, ""),
        cuad_category=category,
        question=question,
        answers=answers,
        is_impossible=impossible,
        qa_id=qa_id,
    )


def load_contracts(
    path: Path,
    clauses: list[ClauseSpec],
    *,
    strict: bool = True,
    limit: int | None = None,
    keep_unenabled: bool = False,
) -> list[ContractRecord]:
    """Load a CUAD file into ContractRecords.

    Only the supplied clause categories are kept (question -> category parse is
    validated against the clause registry). `strict=True` validates every gold
    answer against the context and raises CuadDataError on any mismatch.

    limit: optional cap on contracts loaded (for smoke tests).
    keep_unenabled: if True, keep QAs of unregistered categories with an empty
        clause_label (used by dataset audits, not by feature preparation).
    """
    enabled_by_category = {c.cuad_category: c for c in clauses if c.enabled}
    label_for_category = {c.cuad_category: c.label for c in clauses if c.enabled}
    question_for_category = {c.cuad_category: c.question for c in clauses if c.enabled}
    known_categories = set(label_for_category)

    records: list[ContractRecord] = []
    if not path.exists():
        raise ConfigError(f"CUAD file not found: {path}. Extract data.zip into data/raw/ first.")

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    for item in payload["data"]:
        if limit is not None and len(records) >= limit:
            break
        title = item.get("title", "")
        if not title:
            raise CuadDataError("Contract with empty title found.")
        for para in item.get("paragraphs", []):
            context = para.get("context", "")
            if not context.strip():
                raise CuadDataError(f"Empty context in contract '{title}'.")
            qas: list[ClauseQA] = []
            for qa in para.get("qas", []):
                m = CATEGORY_RE.search(qa.get("question", ""))
                if not m:
                    raise CuadDataError(
                        f"Cannot parse category from question in contract '{title}' "
                        f"qa '{qa.get('id', '')}'"
                    )
                category = m.group(1)
                if category not in known_categories and not keep_unenabled:
                    continue
                parsed = _parse_qa(
                    qa,
                    category,
                    question_for_category.get(category, qa.get("question", "")),
                    label_for_category,
                    title,
                    context,
                    strict,
                )
                if parsed is not None:
                    qas.append(parsed)
            records.append(ContractRecord(contract_id=title, context=context, qas=qas))

    ids = [r.contract_id for r in records]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise CuadDataError(f"Duplicate contract titles in {path.name}: {sorted(dupes)[:5]}")
    return records


def load_train_contracts(clauses: list[ClauseSpec], **kwargs) -> list[ContractRecord]:
    """Load the official training file (exploded Category_N QA instances)."""
    return load_contracts(TRAIN_SEPARATE_PATH, clauses, **kwargs)


def load_test_contracts(clauses: list[ClauseSpec], **kwargs) -> list[ContractRecord]:
    """Load the official held-out test file (gold answers included).

    Used for the untouched final evaluation only - never for tuning.
    """
    return load_contracts(TEST_PATH, clauses, **kwargs)


def load_merged_contracts(clauses: list[ClauseSpec], **kwargs) -> list[ContractRecord]:
    """Load the merged superset file (audits / sample extraction)."""
    return load_contracts(CUADV1_PATH, clauses, **kwargs)
