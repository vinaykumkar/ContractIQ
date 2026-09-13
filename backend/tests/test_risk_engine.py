"""Risk engine tests: determinism, bands, confidence-awareness, no-clause."""
from __future__ import annotations

from app.risk.engine import evaluate_risk
from app.risk.rules import RISK_RULES, rules_for

ALL_LABELS = sorted({r.clause_label for r in RISK_RULES})


def clause(label, found, text="", confidence=0.9):
    return {"clause_type": label, "found": found, "text": text,
            "confidence": confidence, "start_char": 0 if found else -1,
            "end_char": len(text) if found else -1}


def full_results(**overrides) -> list[dict]:
    """All 15 clause labels; default found=False (absence rules fire), overridable.

    With everything absent the baseline score is 22
    (TERMINATION_CONVENIENCE_ABSENT 10 + CAP_ON_LIABILITY_ABSENT 12).
    """
    results = []
    for label in ALL_LABELS:
        if label in overrides:
            results.append(overrides[label])
        else:
            results.append(clause(label, False))
    return results


BASELINE_ABSENT_SCORE = 22


class TestScoring:
    def test_present_restrictive_clauses_score(self, settings):
        risk = evaluate_risk(full_results(
            non_compete=clause("non_compete", True, "shall not compete", 0.9),
            exclusivity=clause("exclusivity", True, "exclusively", 0.85),
        ), settings)
        ids = {f.rule_id for f in risk.findings}
        assert "NON_COMPETE_PRESENT" in ids and "EXCLUSIVITY_PRESENT" in ids
        assert risk.overall_score == BASELINE_ABSENT_SCORE + 18 + 15
        assert risk.overall_level == "MEDIUM"  # 55 <= 60

    def test_deterministic(self, settings):
        results = full_results(
            non_compete=clause("non_compete", True, "shall not compete", 0.9),
            renewal_term=clause("renewal_term", True, "shall automatically renew", 0.8),
        )
        r1 = evaluate_risk(results, settings)
        r2 = evaluate_risk(results, settings)
        assert r1.overall_score == r2.overall_score
        assert [f.rule_id for f in r1.findings] == [f.rule_id for f in r2.findings]

    def test_no_clauses_found(self, settings):
        risk = evaluate_risk([], settings)
        assert risk.overall_score == BASELINE_ABSENT_SCORE
        assert risk.overall_level == "LOW"
        ids = {f.rule_id for f in risk.findings}
        assert "TERMINATION_CONVENIENCE_ABSENT" in ids
        assert "CAP_ON_LIABILITY_ABSENT" in ids

    def test_score_capped_at_100(self, settings):
        results = [clause(r.clause_label, True, "shall automatically renew without the prior written consent", 0.99)
                   for r in RISK_RULES]
        risk = evaluate_risk(results, settings)
        assert risk.overall_score <= 100


class TestBands:
    def test_medium_band(self, settings):
        # baseline 22 + non_compete 18 + exclusivity 15 = 55 -> MEDIUM (31-60)
        r = evaluate_risk(full_results(
            non_compete=clause("non_compete", True, "x", 0.99),
            exclusivity=clause("exclusivity", True, "x", 0.99),
        ), settings)
        assert r.overall_score == 55 and r.overall_level == "MEDIUM"

    def test_low_band(self, settings):
        # baseline 22 + informational-only governing_law (weight 0) -> LOW
        r = evaluate_risk(full_results(
            governing_law=clause("governing_law", True, "Delaware", 0.99)), settings)
        assert r.overall_score == BASELINE_ABSENT_SCORE and r.overall_level == "LOW"

    def test_high_band(self, settings):
        # 22 + non_compete 18 + exclusivity 15 + renewal present 5 + auto-renew 10 = 70
        r = evaluate_risk(full_results(
            non_compete=clause("non_compete", True, "x", 0.99),
            exclusivity=clause("exclusivity", True, "x", 0.99),
            renewal_term=clause("renewal_term", True, "shall automatically renew", 0.99),
        ), settings)
        assert r.overall_score == 70 and r.overall_level == "HIGH"


class TestConfidenceAwareness:
    def test_low_confidence_present_rule_is_uncertain_and_unscored(self, settings):
        risk = evaluate_risk(full_results(
            non_compete=clause("non_compete", True, "shall not compete", 0.10)), settings)
        f = next(x for x in risk.findings if x.rule_id == "NON_COMPETE_PRESENT")
        assert f.uncertain is True
        assert f.weight == 0
        assert risk.overall_score == BASELINE_ABSENT_SCORE  # non-compete not scored

    def test_found_false_never_triggers_present_rule(self, settings):
        r = evaluate_risk(full_results(non_compete=clause("non_compete", False)), settings)
        assert not any(f.rule_id == "NON_COMPETE_PRESENT" for f in r.findings)

    def test_confidence_and_severity_kept_separate(self, settings):
        r = evaluate_risk(full_results(
            non_compete=clause("non_compete", True, "x", 0.42)), settings)
        f = next(x for x in r.findings if x.rule_id == "NON_COMPETE_PRESENT")
        assert f.severity == "HIGH"       # rule severity unchanged
        assert f.confidence == 0.42       # ML confidence reported as-is
        assert f.uncertain is True        # 0.42 < default min_confidence 0.5 -> unscored
        assert f.weight == 0

    def test_wording_rule_requires_pattern(self, settings):
        # renewal text WITHOUT auto-renew wording -> only the base rule (weight 5)
        r1 = evaluate_risk(full_results(
            renewal_term=clause("renewal_term", True, "one year term", 0.9)), settings)
        # renewal text WITH auto-renew wording -> base (5) + auto-renew (10)
        r2 = evaluate_risk(full_results(
            renewal_term=clause("renewal_term", True, "shall automatically renew", 0.9)), settings)
        assert r2.overall_score == r1.overall_score + 10


class TestRulesRegistry:
    def test_all_rules_have_required_fields(self):
        for r in RISK_RULES:
            assert r.rule_id and r.clause_label and r.trigger
            assert r.severity in {"INFO", "LOW", "MEDIUM", "HIGH"}
            assert 0 <= r.weight <= 25
            assert r.reason and r.explanation
            if r.trigger == "wording":
                assert r.wording_pattern

    def test_unique_rule_ids(self):
        ids = [r.rule_id for r in RISK_RULES]
        assert len(ids) == len(set(ids))

    def test_rules_cover_enabled_clauses(self):
        import json
        from pathlib import Path

        registry = json.loads(
            Path(__file__).resolve().parents[2].joinpath("ml/configs/clauses.json").read_text("utf-8")
        )
        enabled = {c["label"] for c in registry["clauses"] if c["enabled"]}
        covered = {r.clause_label for r in RISK_RULES}
        assert covered <= enabled  # rules only for enabled clauses
