#!/usr/bin/env python
"""Phase 3 retrieval recall experiment (validation only, no model needed).

Measures, for K in {2,3,5,8,10,15}:
- gold-answer recall: % of gold spans fully covered by selected regions
- window reduction: estimated char-level reduction vs full-document inference
per clause, so per-clause fallbacks can be configured.

Writes reports/phase3_retrieval_recall.{json,md}.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.src.config import REPORTS_DIR, load_enabled_clauses  # noqa: E402
from ml.src.cuad_loader import load_train_contracts  # noqa: E402
from ml.src.preprocessing import VAL, assign_splits  # noqa: E402
from ml.src.retrieval import select_regions, regions_cover, split_blocks  # noqa: E402

K_VALUES = [2, 3, 5, 8, 10, 15]
BLOCK_CHARS = 1200
OVERLAP_CHARS = 200
CHARS_PER_TOKEN = 4.27  # measured in Phase 1 (78,591 tokens / 335,282 chars on longest)


def main() -> int:
    clauses = load_enabled_clauses()

    records = load_train_contracts(clauses, strict=True)
    assign_splits(records, seed=42, val_fraction=0.10)
    val = [r for r in records if r.split == VAL]
    print(f"Val contracts: {len(val)}")

    variants = {
        "plain_question": {"use_keywords": False, "boost_first_blocks": 0},
        "keywords": {"use_keywords": True, "boost_first_blocks": 0},
        "keywords_plus_title_boost": {"use_keywords": True, "boost_first_blocks": 2},
    }
    per_clause = {c.label: {v: {k: {"gold_spans": 0, "covered": 0} for k in K_VALUES}
                            for v in variants} for c in clauses}

    for rec in val:
        for clause in clauses:
            golds = [(qa.answers[0].start, qa.answers[0].end)
                     for qa in rec.qas_for(clause.label)
                     if not qa.is_impossible and qa.answers]
            for vname, vcfg in variants.items():
                for k in K_VALUES:
                    stats = per_clause[clause.label][vname][k]
                    stats["gold_spans"] += len(golds)
                    regions = select_regions(rec.context, clause, k, BLOCK_CHARS, OVERLAP_CHARS, **vcfg)
                    for gs, ge in golds:
                        if regions_cover(regions, gs, ge):
                            stats["covered"] += 1

    summary = {}
    for clause in clauses:
        summary[clause.label] = {}
        for vname in variants:
            summary[clause.label][vname] = {}
            for k in K_VALUES:
                s = per_clause[clause.label][vname][k]
                recall = s["covered"] / s["gold_spans"] if s["gold_spans"] else None
                summary[clause.label][vname][k] = {
                    "gold_spans": s["gold_spans"],
                    "covered": s["covered"],
                    "recall": round(recall, 4) if recall is not None else None,
                }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "val_contracts": len(val),
        "block_config": {"max_block_chars": BLOCK_CHARS, "overlap_chars": OVERLAP_CHARS},
        "k_values": K_VALUES,
        "variants": list(variants),
        "per_clause": summary,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "phase3_retrieval_recall.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = ["# ContractIQ — Phase 3 Retrieval Recall (validation)", "",
          f"_Generated: {report['generated_at']}_ · {len(val)} val contracts · "
          f"blocks of {BLOCK_CHARS} chars with {OVERLAP_CHARS} overlap · TF-IDF ranking", "",
          "Gold-answer recall = % of gold spans intersecting selected regions.", ""]
    for vname in variants:
        md += [f"## Variant: {vname}", "",
               "| Clause | " + " | ".join(f"K={k}" for k in K_VALUES) + " |",
               "|---|" + "---:|" * len(K_VALUES)]
        for clause in clauses:
            row = [clause.label]
            for k in K_VALUES:
                r = summary[clause.label][vname][k]["recall"]
                row.append("n/a" if r is None else f"{r*100:.1f}%")
            md.append("| " + " | ".join(row) + " |")
        md.append("")
    md += ["## Aggregate recall across clauses", "",
           "| Variant | " + " | ".join(f"K={k}" for k in K_VALUES) + " |",
           "|---|" + "---:|" * len(K_VALUES)]
    for vname in variants:
        row = [vname]
        for k in K_VALUES:
            tot = sum(per_clause[c.label][vname][k]["gold_spans"] for c in clauses)
            cov = sum(per_clause[c.label][vname][k]["covered"] for c in clauses)
            row.append(f"{cov / tot * 100:.1f}%" if tot else "n/a")
        md.append("| " + " | ".join(row) + " |")
    (REPORTS_DIR / "phase3_retrieval_recall.md").write_text("\n".join(md), encoding="utf-8")
    print("Wrote reports/phase3_retrieval_recall.{json,md}")
    return 0


def merge_ranges(regions):
    spans = sorted((r.start, r.end) for r in regions)
    merged = [list(spans[0])] if spans else []
    for s, e in spans[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


if __name__ == "__main__":
    sys.exit(main())
