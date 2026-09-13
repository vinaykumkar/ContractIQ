"""Deterministic, confidence-aware risk scoring.

Input: the clause results of one analysis, in the shape produced by the
Phase 3 inference API ({"clause_type", "found", "text", "confidence", ...}).

Rules:
- `present` rules fire only on found=True with confidence >= rule.min_confidence;
  below that threshold the finding is emitted as `uncertain` and EXCLUDED from
  the score (never silently promoted, never silently dropped).
- `absent` rules fire on found=False (no confidence involved).
- `wording` rules additionally require the regex to match the extracted text.
- Weight 0 rules are informational and never change the score.
- Score = sum of weights of certain findings, capped at 100. Bands are read
  from the central registry (0-30 LOW / 31-60 MEDIUM / 61-100 HIGH).
- The function is pure: same inputs -> same outputs.
"""
from __future__ import annotations

import re

from ..core.config import Settings, load_settings, risk_bands
from .models import RiskFinding, RiskResult
from .rules import RISK_RULES


def _band(score: int, bands: dict) -> str:
    if score <= bands["low_max"]:
        return "LOW"
    if score <= bands["medium_max"]:
        return "MEDIUM"
    return "HIGH"


def _evidence_snippet(text: str, limit: int = 240) -> str:
    t = " ".join((text or "").split())
    return t[:limit] + ("…" if len(t) > limit else "")


def evaluate_risk(
    clause_results: list[dict],
    settings: Settings | None = None,
    min_confidence_override: float | None = None,
) -> RiskResult:
    """Score one analysis deterministically from its clause results."""
    s = settings or load_settings()
    bands = risk_bands(s)
    default_min_conf = min_confidence_override if min_confidence_override is not None else s.risk_min_confidence

    by_label: dict[str, dict] = {}
    for cr in clause_results:
        label = cr.get("clause_type")
        if label is not None:
            by_label[label] = cr

    findings: list[RiskFinding] = []
    score = 0

    for rule in RISK_RULES:
        cr = by_label.get(rule.clause_label)
        found = bool(cr.get("found")) if cr else False
        confidence = float(cr.get("confidence") or 0.0) if cr else 0.0
        text = (cr.get("text") or "") if cr else ""
        min_conf = max(rule.min_confidence, default_min_conf) if rule.trigger != "absent" else 0.0

        if rule.trigger == "absent":
            fired = not found
            uncertain = False
            evidence = ""
        elif rule.trigger == "present":
            fired = found
            uncertain = found and confidence < min_conf
            evidence = _evidence_snippet(text)
        else:  # wording
            matched = bool(re.search(rule.wording_pattern, text)) if text else False
            fired = found and matched
            uncertain = fired and confidence < min_conf
            evidence = _evidence_snippet(text)

        if not fired:
            continue

        weight_applied = 0 if (rule.weight == 0 or uncertain) else rule.weight
        score += weight_applied
        findings.append(RiskFinding(
            rule_id=rule.rule_id,
            clause_type=rule.clause_label,
            severity=rule.severity,
            weight=weight_applied,
            reason=rule.reason + (" (low ML confidence - not scored)" if uncertain else ""),
            evidence=evidence,
            confidence=confidence,
            uncertain=uncertain,
            explanation=rule.explanation,
            recommendation=rule.recommendation,
        ))

    score = min(score, 100)
    return RiskResult(
        overall_score=score,
        overall_level=_band(score, bands),
        findings=findings,
        bands=bands,
    )
