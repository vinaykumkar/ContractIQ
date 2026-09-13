#!/usr/bin/env python
"""ContractIQ - Phase 1 CUAD dataset analysis.

Analyses the extracted CUAD files in data/raw/ and writes:
  reports/dataset_analysis.json
  reports/dataset_analysis.md

Usage (from anywhere - all paths resolve relative to the project root):
    python scripts/analyze_dataset.py
    python scripts/analyze_dataset.py --no-tokenizer   # skip HF tokenizer, use word approximation

The script never modifies data.zip or data/raw/.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"

FILES = ["CUADv1.json", "train_separate_questions.json", "test.json"]

# Question text pattern is identical in every file, so category names are
# parsed from the question itself (robust) and cross-checked against QA ids.
CATEGORY_RE = re.compile(r'related to "(.+?)" that should be reviewed')

# The 15 Version-1 clauses (spec section 4) mapped to the ACTUAL CUAD
# category names - verified against the dataset at runtime below.
V1_TARGET_LABELS = {
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

# Inference-window planning parameters (also Phase 2 defaults; configurable there)
MAX_SEQ_LEN = 512
DOC_STRIDE = 128
QUESTION_OVERHEAD = 3  # [CLS], [SEP], [SEP]


def pct(sorted_vals: list[int], p: float) -> int:
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, max(0, round(p / 100 * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def distribution(values: list[int]) -> dict:
    sv = sorted(values)
    return {
        "min": sv[0] if sv else 0,
        "p25": pct(sv, 25),
        "median": int(median(sv)) if sv else 0,
        "mean": round(mean(sv), 1) if sv else 0,
        "p75": pct(sv, 75),
        "p90": pct(sv, 90),
        "p95": pct(sv, 95),
        "p99": pct(sv, 99),
        "max": sv[-1] if sv else 0,
    }


def load_tokenizer():
    """Try to load the planned baseline tokenizer; return None on failure."""
    try:
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained("distilbert-base-uncased", use_fast=True)
    except Exception as exc:  # network down, transformers missing, etc.
        print(f"  [warn] HF tokenizer unavailable ({type(exc).__name__}); "
              "falling back to word-count approximation.", file=sys.stderr)
        return None


def analyze_file(path: Path, tok) -> dict:
    """Single pass over one CUAD file; keeps only aggregates + light rows."""
    categories: dict[str, dict] = {}
    qa_ids = Counter()
    titles = Counter()
    contract_rows: list[dict] = []
    issues = {
        "missing_fields": 0,
        "empty_context": 0,
        "answer_out_of_bounds": 0,
        "answer_text_mismatch": 0,
        "answer_text_mismatch_normalized": 0,
        "impossible_with_answers": 0,
        "possible_without_answers": 0,
        "duplicate_qa_ids": 0,
        "duplicate_contract_titles": 0,
        "category_parse_failures": 0,
    }
    total_qas = 0

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    for item in payload["data"]:
        title = item.get("title", "")
        for para in item.get("paragraphs", []):
            context = para.get("context", "")
            qas = para.get("qas", [])
            titles[title] += 1
            tokens = (len(tok(context, add_special_tokens=False)["input_ids"])
                      if tok is not None else int(round(len(context.split()) / 0.75)))
            contract_rows.append({
                "title": title, "chars": len(context),
                "words": len(context.split()), "tokens": tokens,
            })
            if not context.strip():
                issues["empty_context"] += 1

            for qa in qas:
                total_qas += 1
                qtext = qa.get("question", "")
                qid = qa.get("id", "")
                answers = qa.get("answers")
                impossible = bool(qa.get("is_impossible", False))

                if not qtext or not qid or answers is None:
                    issues["missing_fields"] += 1
                    continue
                qa_ids[qid] += 1

                m = CATEGORY_RE.search(qtext)
                if not m:
                    issues["category_parse_failures"] += 1
                    continue
                cat = m.group(1)

                cstats = categories.setdefault(cat, {
                    "questions": 0, "positive": 0, "no_answer": 0,
                    "answer_char_lengths": [], "question_token_lengths": [],
                    "detail_variants": set(),
                })
                cstats["questions"] += 1
                cstats["detail_variants"].add(qtext.split("Details:", 1)[-1].strip()[:200])
                if tok is not None:
                    cstats["question_token_lengths"].append(
                        len(tok(qtext, add_special_tokens=False)["input_ids"]))

                if impossible:
                    cstats["no_answer"] += 1
                    if answers:
                        issues["impossible_with_answers"] += 1
                elif answers:
                    cstats["positive"] += 1
                else:
                    issues["possible_without_answers"] += 1

                for ans in answers:
                    text = ans.get("text", "")
                    start = ans.get("answer_start", -1)
                    cstats["answer_char_lengths"].append(len(text))
                    if start < 0 or start + len(text) > len(context):
                        issues["answer_out_of_bounds"] += 1
                    elif context[start:start + len(text)] != text:
                        issues["answer_text_mismatch"] += 1
                        if " ".join(context[start:start + len(text)].split()) != " ".join(text.split()):
                            issues["answer_text_mismatch_normalized"] += 1

    del payload

    cat_rollup = {}
    for cat, st in sorted(categories.items()):
        cat_rollup[cat] = {
            "questions": st["questions"],
            "positive": st["positive"],
            "no_answer": st["no_answer"],
            "positivity_rate": round(st["positive"] / st["questions"], 4) if st["questions"] else 0,
            "answer_char_len": distribution(st["answer_char_lengths"]),
            "question_token_len": distribution(st["question_token_lengths"]),
            "detail_variants": len(st["detail_variants"]),
        }

    return {
        "file": path.name,
        "size_on_disk": path.stat().st_size,
        "contracts": len(titles),
        "total_qas": total_qas,
        "n_categories": len(cat_rollup),
        "categories": cat_rollup,
        "contract_rows": contract_rows,
        "issues": {
            **issues,
            "duplicate_qa_ids": sum(1 for c in qa_ids.values() if c > 1),
            "duplicate_contract_titles": sum(1 for c in titles.values() if c > 1),
        },
    }


def windows_needed(tokens: int, q_len: int) -> int:
    """Sliding-window chunk count for one contract for one clause question."""
    first_cap = MAX_SEQ_LEN - q_len - QUESTION_OVERHEAD
    if tokens <= first_cap:
        return 1
    extra = tokens - first_cap
    return 1 + -(-extra // DOC_STRIDE)  # ceil division


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tokenizer", action="store_true",
                    help="skip HF tokenizer download; approximate tokens from words")
    args = ap.parse_args()

    if not all((RAW_DIR / f).exists() for f in FILES):
        print("ERROR: data/raw/ is missing the extracted CUAD files. "
              "Run the extraction step first.", file=sys.stderr)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    tok = None
    token_method = "word_approximation"
    if not args.no_tokenizer:
        print("Loading tokenizer (distilbert-base-uncased, cached after first run)...")
        tok = load_tokenizer()
        if tok is not None:
            token_method = "distilbert-base-uncased"

    results: dict[str, dict] = {}
    for fname in FILES:
        print(f"Analyzing {fname} ...")
        results[fname] = analyze_file(RAW_DIR / fname, tok)

    cuadv1, train, test = (results["CUADv1.json"],
                           results["train_separate_questions.json"],
                           results["test.json"])

    # Verify the V1 clause names against the ACTUAL dataset categories
    all_cats = set(cuadv1["categories"].keys())
    missing_targets = [c for c in V1_TARGET_LABELS if c not in all_cats]
    if missing_targets:
        print(f"FATAL: expected clause categories not found in dataset: {missing_targets}",
              file=sys.stderr)
        return 1

    # Length distributions + longest contracts
    token_stats, char_stats, longest = {}, {}, []
    for fname, res in results.items():
        rows = res["contract_rows"]
        token_stats[fname] = distribution([r["tokens"] for r in rows])
        char_stats[fname] = distribution([r["chars"] for r in rows])
        longest.extend({"file": fname, "title": r["title"],
                        "tokens": r["tokens"], "chars": r["chars"]} for r in rows)
    longest.sort(key=lambda x: -x["tokens"])
    seen_titles: set[str] = set()
    longest_unique = [x for x in longest
                      if x["title"] not in seen_titles and not seen_titles.add(x["title"])]

    # Question-token overhead per category, measured from the actual questions
    # (all CUAD questions share one template, but the "Details:" text varies)
    sample_q = ('Highlight the parts (if any) of this contract related to "Parties" '
                'that should be reviewed by a lawyer. Details: The two or more entities '
                'who signed this contract')
    fallback_q_len = len(tok(sample_q, add_special_tokens=False)["input_ids"]) if tok is not None else 30
    per_cat_q_len = {}
    for cat in all_cats:
        dist = cuadv1["categories"].get(cat, {}).get("question_token_len", {})
        per_cat_q_len[cat] = dist.get("median") or fallback_q_len

    # Chunking projection for the 15 enabled clauses
    chunk_estimates = {}
    for cat, label in V1_TARGET_LABELS.items():
        q_len = per_cat_q_len[cat]
        w_train = sum(windows_needed(r["tokens"], q_len) for r in train["contract_rows"])
        w_test = sum(windows_needed(r["tokens"], q_len) for r in test["contract_rows"])
        chunk_estimates[label] = {"cuad_category": cat, "question_tokens_median": q_len,
                                  "train_windows": w_train, "test_windows": w_test}
    total_train_windows = sum(v["train_windows"] for v in chunk_estimates.values())
    total_test_windows = sum(v["test_windows"] for v in chunk_estimates.values())

    # Per-category train/test split
    category_split = {}
    for cat in sorted(all_cats):
        t, s = train["categories"].get(cat, {}), test["categories"].get(cat, {})
        category_split[cat] = {
            "train_positive": t.get("positive", 0), "test_positive": s.get("positive", 0),
            "train_questions": t.get("questions", 0), "test_questions": s.get("questions", 0),
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "CUAD v1 (Henriksson et al., 2021) supplied via data.zip",
        "version_stored_in_files": "aok_v1.0",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "tokenizer": token_method,
            "question_token_overhead_median": fallback_q_len,
            "torch_cuda_available": _torch_cuda(),
        },
        "window_config": {"max_seq_len": MAX_SEQ_LEN, "doc_stride": DOC_STRIDE},
        "files": {
            fname: {
                "contracts": res["contracts"],
                "total_qas": res["total_qas"],
                "n_categories": res["n_categories"],
                "issues": res["issues"],
                "contract_char_lengths": char_stats[fname],
                "contract_token_lengths": token_stats[fname],
            }
            for fname, res in results.items()
        },
        "split_integrity": {
            "cuadv1_contracts": cuadv1["contracts"],
            "train_contracts": train["contracts"],
            "test_contracts": test["contracts"],
            "sum_matches_full": train["contracts"] + test["contracts"] == cuadv1["contracts"],
        },
        "categories": {
            "count": len(all_cats),
            "per_category_cuadv1": cuadv1["categories"],
            "per_category_train": train["categories"],
            "per_category_test": test["categories"],
            "train_test_split": category_split,
        },
        "longest_contracts_top10": longest_unique[:10],
        "enabled_clauses_v1": chunk_estimates,
        "inference_cost_projection": {
            "total_train_windows_15clauses": total_train_windows,
            "total_test_windows_15clauses": total_test_windows,
            "note": "Windows = sliding-window chunks per contract per clause at "
                    "max_seq_len=512, stride=128.",
        },
        "data_quality": {
            "cuadv1_issues": cuadv1["issues"],
            "train_issues": train["issues"],
            "test_issues": test["issues"],
        },
    }

    json_path = REPORTS_DIR / "dataset_analysis.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (REPORTS_DIR / "dataset_analysis.md").write_text(build_md(report), encoding="utf-8")

    print(f"\nWrote {json_path}")
    print(f"Wrote {REPORTS_DIR / 'dataset_analysis.md'}")
    print("\n=== Quick summary ===")
    print(f"Contracts: {cuadv1['contracts']} (train {train['contracts']} / test {test['contracts']})")
    print(f"Categories: {len(all_cats)}")
    print(f"Token method: {token_method} (question overhead ~{fallback_q_len} tokens median)")
    print(f"Train windows (15 clauses): {total_train_windows:,} | Test windows: {total_test_windows:,}")
    return 0


def _torch_cuda() -> bool | None:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return None


def build_md(r: dict) -> str:
    f = r["files"]
    dq = r["data_quality"]
    lines: list[str] = []
    a = lines.append
    a("# ContractIQ — CUAD Dataset Analysis")
    a("")
    a(f"_Generated: {r['generated_at']}_ · Token counting: `{r['environment']['tokenizer']}` · "
      f"CUDA available: `{r['environment']['torch_cuda_available']}`")
    a("")
    a("## 1. Files & split")
    a("")
    a("| File | Contracts | QAs | Categories |")
    a("|---|---:|---:|---:|")
    for name, res in f.items():
        a(f"| {name} | {res['contracts']} | {res['total_qas']:,} | {res['n_categories']} |")
    a("")
    si = r["split_integrity"]
    a(f"Train ({si['train_contracts']}) + test ({si['test_contracts']}) contracts exactly partition the "
      f"{si['cuadv1_contracts']} contracts of CUADv1.json: **{si['sum_matches_full']}**. "
      "test.json ships gold answers and is the honest evaluation set; CUADv1.json is the merged superset; "
      "train_separate_questions.json explodes each annotated span into its own QA instance (`Category_N` ids).")
    a("")
    a("## 2. Contract length distribution")
    a("")
    a("| File | Metric | min | p25 | median | mean | p75 | p90 | p95 | p99 | max |")
    a("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, res in f.items():
        t = res["contract_token_lengths"]
        a(f"| {name} | tokens | {t['min']:,} | {t['p25']:,} | {t['median']:,} | {t['mean']:,} | "
          f"{t['p75']:,} | {t['p90']:,} | {t['p95']:,} | {t['p99']:,} | {t['max']:,} |")
    a("")
    a("Longest contracts (tokens):")
    a("")
    for x in r["longest_contracts_top10"][:5]:
        a(f"- {x['title']} — {x['tokens']:,} tokens ({x['chars']:,} chars)")
    a("")
    a("## 3. Clause categories")
    a("")
    a("Positivity = share of QA pairs with at least one annotated span (CUADv1 file). "
      "Categories sorted by positive count.")
    a("")
    a("| Category | QAs | Positive | No-answer | Positivity | Train+ inst. | Test+ inst. |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    split = r["categories"]["train_test_split"]
    for cat, st in sorted(r["categories"]["per_category_cuadv1"].items(),
                          key=lambda kv: -kv[1]["positive"]):
        sp = split[cat]
        a(f"| {cat} | {st['questions']} | {st['positive']} | {st['no_answer']} | "
          f"{st['positivity_rate']*100:.1f}% | {sp['train_positive']} | {sp['test_positive']} |")
    a("")
    a("## 4. Version-1 enabled clauses (15)")
    a("")
    a("| Label | CUAD category | Question tokens (median) | Train windows | Test windows |")
    a("|---|---|---:|---:|---:|")
    for label, v in r["enabled_clauses_v1"].items():
        a(f"| `{label}` | {v['cuad_category']} | {v['question_tokens_median']} | "
          f"{v['train_windows']:,} | {v['test_windows']:,} |")
    ic = r["inference_cost_projection"]
    a("")
    a(f"Total sliding-window chunks at max_seq_len={r['window_config']['max_seq_len']}, "
      f"stride={r['window_config']['doc_stride']}: **{ic['total_train_windows_15clauses']:,}** train / "
      f"**{ic['total_test_windows_15clauses']:,}** test.")
    a("")
    a("## 5. Data quality")
    a("")
    a("| Check | CUADv1 | train | test |")
    a("|---|---:|---:|---:|")
    for k in f["CUADv1.json"]["issues"]:
        a(f"| {k} | {dq['cuadv1_issues'][k]} | {dq['train_issues'][k]} | {dq['test_issues'][k]} |")
    a("")
    a("## 6. Notes for modelling")
    a("")
    a("- Category imbalance is strong (see Positivity column): head categories such as `Document Name` "
      "or `Governing Law` are positive in nearly every contract; several tail categories sit below 10%. "
      "Use per-category metrics and no-answer-aware evaluation.")
    a("- Training should consume `train_separate_questions.json` (one QA instance per annotated span); "
      "evaluation should use `test.json` and deduplicate spans per category.")
    a("- Gold answers may differ from the raw context slice by whitespace; exact and normalized "
      "mismatch counters are reported above and preprocessing must tolerate this.")
    a("- These statistics describe the dataset only. AI-assisted analysis; results should be reviewed "
      "by a qualified professional.")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
