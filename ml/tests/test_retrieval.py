"""Tests for retrieval block splitting, ranking, and gold-span retention."""
from __future__ import annotations

from ml.src.retrieval import (
    CLAUSE_KEYWORDS,
    build_query,
    merge_regions,
    regions_cover,
    select_regions,
    split_blocks,
)

from conftest import make_clause


def test_split_blocks_covers_whole_context():
    context = " ".join(f"word{i}" for i in range(2000))
    blocks = split_blocks(context, max_block_chars=800, overlap_chars=150)
    assert blocks, "blocks must exist"
    assert blocks[0].start == 0
    assert blocks[-1].end == len(context)
    # consecutive blocks overlap
    for a, b in zip(blocks, blocks[1:]):
        assert b.start < a.end


def test_split_blocks_respects_max_size():
    context = " ".join(f"word{i}" for i in range(5000))
    for b in split_blocks(context, max_block_chars=800, overlap_chars=150):
        assert b.end - b.start <= 810  # small tolerance for whitespace alignment


def test_split_blocks_empty_context():
    assert split_blocks("", 800, 150) == []
    assert split_blocks("   \n  ", 800, 150) == []


def test_build_query_includes_keywords_and_details():
    clause = make_clause("governing_law", "Governing Law")
    q = build_query(clause, use_keywords=True)
    assert "Governing Law" in q
    for kw in CLAUSE_KEYWORDS["governing_law"][:3]:
        assert kw in q
    plain = build_query(clause, use_keywords=False)
    assert "laws of the state" not in plain


def test_select_regions_is_deterministic_and_bounded():
    context = " ".join(f"token{i}" for i in range(3000))
    clause = make_clause("governing_law", "Governing Law")
    r1 = select_regions(context, clause, top_k=5)
    r2 = select_regions(context, clause, top_k=5)
    assert r1 == r2
    assert len(r1) <= 5 + 2  # top_k + title boost


def test_select_regions_title_boost_includes_first_block():
    context = " ".join(f"token{i}" for i in range(3000))
    clause = make_clause("governing_law", "Governing Law")
    regions = select_regions(context, clause, top_k=3, boost_first_blocks=2)
    starts = {r.start for r in regions}
    assert 0 in starts  # first block always present


def test_regions_cover_and_merge():
    clause = make_clause("governing_law", "Governing Law")
    context = ("GENERIC PREAMBLE WORDS. " * 20
               + "This agreement is governed by the laws of the state of Delaware. "
               + "FILLER SENTENCE WORDS. " * 40)
    regions = select_regions(context, clause, top_k=3)
    gold_start = context.index("governed by the laws")
    gold_end = gold_start + len("governed by the laws of the state of Delaware")
    assert regions_cover(regions, gold_start, gold_end), \
        "keyword-rich block containing the gold clause must be selected"

    merged = merge_regions(regions)
    assert merged == sorted(merged)
    for (s1, e1), (s2, e2) in zip(merged, merged[1:]):
        assert e1 < s2  # disjoint after merging


def test_regions_cover_miss_is_detectable():
    clause = make_clause("non_compete", "Non-Compete")
    context = "UNRELATED WORDS ONLY HERE. " * 200 + "finally something else"
    regions = select_regions(context, clause, top_k=2, boost_first_blocks=0)
    assert not regions_cover(regions, len(context) - 20, len(context) - 5)
