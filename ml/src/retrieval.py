"""Lightweight lexical retrieval stage to reduce QA inference cost.

Splits a contract into overlapping character blocks, ranks them against each
clause's question with TF-IDF cosine similarity (scikit-learn, fully local),
and selects the top-K blocks as the regions the QA model sees.

Design constraints:
- free/local only (no servers, no vector DBs)
- deterministic and reproducible
- recall-first: the evaluation framework measures what fraction of gold answers
  remain inside selected regions; per-clause fallback to full-document
  inference is configured centrally in ml/configs/model.json.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .config import ClauseSpec

QUESTION_TEMPLATE_RE = re.compile(r"^.*?that should be reviewed by a lawyer\.\s*", re.DOTALL)

_WS_RE = re.compile(r"\s+")

# Transparent, per-clause keyword expansions for lexical ranking. CUAD
# questions describe concepts in generic legal language; the clause text often
# uses different vocabulary, so plain question TF-IDF loses gold answers.
# These lexicons are engineering decisions, stored in code, and measured by
# the retrieval recall experiment. They do NOT affect the QA model itself.
CLAUSE_KEYWORDS: dict[str, list[str]] = {
    "document_name": ["agreement", "contract", "exhibit", "statement of work", "amendment", "title"],
    "parties": ["by and between", "by and among", "party", "parties", "between", "corporation",
                "limited liability company", "l.l.c.", "llc", "inc.", "ltd", "hereinafter referred to as"],
    "agreement_date": ["dated", "dated as of", "made and entered into", "this agreement is made",
                       "day of", "effective date of this agreement", "by and between"],
    "effective_date": ["effective", "effective date", "commence", "commencement", "shall take effect",
                       "as of the date"],
    "expiration_date": ["expire", "expiration", "term of this agreement", "shall terminate",
                        "until", "expires on"],
    "renewal_term": ["renew", "renewal", "automatically renew", "successive", "extend", "extension"],
    "governing_law": ["governed by", "laws of the state", "laws of", "jurisdiction", "construed in accordance",
                      "venue", "forum"],
    "termination_for_convenience": ["terminate", "termination", "for convenience", "without cause",
                                    "upon notice"],
    "non_compete": ["non-compete", "not compete", "competing", "competition", "restrict", "solicit",
                    "similar business", "conflict"],
    "exclusivity": ["exclusive", "exclusively", "sole", "shall not", "no other", "exclusivity",
                    "not sell", "not distribute"],
    "anti_assignment": ["assign", "assignment", "assigns", "without the prior written consent",
                        "successors and assigns", "transfer"],
    "license_grant": ["license", "grant", "hereby grants", "non-exclusive", "nonexclusive", "royalty-free",
                      "licensor", "licensee"],
    "audit_rights": ["audit", "inspect", "books and records", "examine", "accounting records",
                     "upon reasonable notice"],
    "cap_on_liability": ["liability", "in no event", "aggregate", "limitation of liability",
                         "consequential damages", "indemnif"],
    "insurance": ["insurance", "insure", "policy", "coverage", "insurance company", "certificate of insurance"],
}


@dataclass(frozen=True)
class Block:
    start: int  # char offset in the original context
    end: int
    index: int


@dataclass(frozen=True)
class Region:
    start: int
    end: int
    score: float
    block_index: int


def split_blocks(context: str, max_block_chars: int = 1200, overlap_chars: int = 200) -> list[Block]:
    """Split context into overlapping blocks aligned to whitespace.

    Blocks never exceed max_block_chars; each block after the first starts at
    most overlap_chars before the previous block ended, so text near a seam is
    covered from both sides. Empty/whitespace contexts return no blocks.
    """
    if not context or not context.strip():
        return []
    blocks: list[Block] = []
    start = 0
    n = len(context)
    index = 0
    while start < n:
        end = min(start + max_block_chars, n)
        if end < n:
            # do not cut a word: back up to the last whitespace inside the window
            ws = _WS_RE.finditer(context[start + int(max_block_chars * 0.5):end + 1])
            last = None
            for m in ws:
                last = m
            if last is not None and last.start() + start + int(max_block_chars * 0.5) > start:
                end = last.start() + start + int(max_block_chars * 0.5)
        blocks.append(Block(start=start, end=end, index=index))
        index += 1
        if end >= n:
            break
        next_start = max(end - overlap_chars, start + 1)
        # align the next start to whitespace so tokens stay whole
        m = _WS_RE.search(context[next_start:end + overlap_chars])
        if m:
            next_start = next_start + m.start() + 1
        start = next_start
    return blocks


def build_query(clause: ClauseSpec, use_keywords: bool = True) -> str:
    """Query for lexical ranking: category + question Details + keyword lexicon.

    The generic template ("Highlight the parts ... reviewed by a lawyer")
    carries no discriminative signal. The keyword lexicon bridges the
    vocabulary gap between question language and clause language; its effect
    is measured in reports/phase3_retrieval_recall.*.
    """
    details = QUESTION_TEMPLATE_RE.sub("", clause.question).strip()
    details = details.split("Details:", 1)[-1].strip() if "Details:" in details else details
    parts = [clause.cuad_category, details]
    if use_keywords:
        parts.extend(CLAUSE_KEYWORDS.get(clause.label, []))
    return " ".join(p for p in parts if p).strip()


def rank_blocks(context: str, query: str, blocks: list[Block]) -> list[tuple[Block, float]]:
    """Rank blocks against the query with TF-IDF cosine similarity."""
    if not blocks:
        return []
    from sklearn.feature_extraction.text import TfidfVectorizer

    texts = [context[b.start : b.end] for b in blocks]
    try:
        vec = TfidfVectorizer(stop_words="english", sublinear_tf=True,
                              strip_accents="unicode", lowercase=True)
        matrix = vec.fit_transform(texts + [query])
    except ValueError:  # empty vocabulary (e.g. stop-word-only contract)
        return [(b, 0.0) for b in blocks]
    q = matrix[-1]
    scores = (matrix[:-1] @ q.T).toarray().ravel()
    ranked = sorted(zip(blocks, scores.tolist()), key=lambda t: (-t[1], t[0].index))
    return ranked


def select_regions(
    context: str,
    clause: ClauseSpec,
    top_k: int,
    max_block_chars: int = 1200,
    overlap_chars: int = 200,
    use_keywords: bool = True,
    boost_first_blocks: int = 1,
) -> list[Region]:
    """Top-K ranked blocks as Regions for one clause, highest score first.

    boost_first_blocks: always include the first N blocks (contract
    title/preamble) - cheap positional prior for Document Name / Parties /
    Agreement Date style clauses whose evidence concentrates up front.
    """
    blocks = split_blocks(context, max_block_chars, overlap_chars)
    if not blocks:
        return []
    ranked = rank_blocks(context, build_query(clause, use_keywords), blocks)
    chosen: list[Block] = [b for b, _ in ranked[: max(1, top_k)]]
    for b in blocks[: max(0, boost_first_blocks)]:
        if all(b.index != c.index for c in chosen):
            chosen.append(b)
    return [
        Region(start=b.start, end=b.end, score=next(
            (round(s, 6) for bb, s in ranked if bb.index == b.index), 0.0),
            block_index=b.index)
        for b in chosen
    ]


def regions_cover(regions: list[Region], char_start: int, char_end: int) -> bool:
    """True if [char_start, char_end) intersects any region (gold recall check)."""
    return any(r.start < char_end and char_start < r.end for r in regions)


def merge_regions(regions: list[Region], gap_chars: int = 0) -> list[tuple[int, int]]:
    """Merge overlapping/adjacent regions into disjoint char ranges (ordered)."""
    if not regions:
        return []
    spans = sorted((r.start, r.end) for r in regions)
    merged = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1] + gap_chars:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]
