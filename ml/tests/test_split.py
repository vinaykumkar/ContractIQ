"""Tests for the deterministic contract-level split and leakage checks."""
from __future__ import annotations

from ml.src.config import TEST_PATH
from ml.src.preprocessing import TRAIN, VAL, assign_splits, leakage_report

from conftest import synthetic_record


def _records(n=100):
    return [synthetic_record(contract_id=f"C{i:03d}") for i in range(n)]


def test_split_is_deterministic():
    recs1, recs2 = _records(), _records()
    info1 = assign_splits(recs1, seed=42, val_fraction=0.1)
    info2 = assign_splits(recs2, seed=42, val_fraction=0.1)
    assert info1.val_ids == info2.val_ids
    assert info1.train_ids == info2.train_ids
    # a different seed produces a different split
    info3 = assign_splits(_records(), seed=7, val_fraction=0.1)
    assert info3.val_ids != info1.val_ids


def test_split_sizes_and_membership():
    recs = _records(100)
    info = assign_splits(recs, seed=42, val_fraction=0.1)
    assert info.counts == {"train": 90, "val": 10}
    assert not (set(info.train_ids) & set(info.val_ids))
    for r in recs:
        if r.contract_id in set(info.val_ids):
            assert r.split == VAL
        else:
            assert r.split == TRAIN


def test_split_never_overlaps_official_test_set():
    """Contract ids of the official test file must never enter train/val."""
    import json

    with TEST_PATH.open("r", encoding="utf-8") as f:
        test_titles = {item["title"] for item in json.load(f)["data"]}

    # train-file contracts are disjoint from test titles (CUAD property);
    # simulate the pipeline and assert the invariant end-to-end
    from ml.src.cuad_loader import load_train_contracts

    from ml.src.config import load_enabled_clauses

    records = load_train_contracts(load_enabled_clauses(), strict=False, limit=50)
    info = assign_splits(records, seed=42, val_fraction=0.1)
    assert not (set(info.train_ids) & test_titles)
    assert not (set(info.val_ids) & test_titles)


def test_leakage_report_clean():
    report = leakage_report(["A", "B"], ["C"], ["D"])
    assert report["train_overlap_val"] == []
    assert report["train_overlap_test"] == []
    assert report["val_overlap_test"] == []
    assert report["counts"] == {"train": 2, "val": 1, "test": 1}


def test_leakage_report_detects_overlap():
    report = leakage_report(["A", "B"], ["B", "C"], ["C"])
    assert report["train_overlap_val"] == ["B"]
    assert report["val_overlap_test"] == ["C"]
