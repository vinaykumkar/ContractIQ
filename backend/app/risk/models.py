"""Risk engine data model.

Risk output is strictly separated from ML confidence: a finding carries both
the ML confidence of the underlying clause extraction AND the heuristic
severity/weight, and they are never merged into one number.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RiskRule:
    """One transparent, deterministic heuristic rule."""

    rule_id: str
    clause_label: str
    trigger: str  # "present" | "absent" | "wording"
    weight: int  # 0 = informational (traceability only)
    severity: str  # "INFO" | "LOW" | "MEDIUM" | "HIGH"
    reason: str
    explanation: str
    recommendation: str = ""
    wording_pattern: str = ""  # regex applied to the extracted clause text
    min_confidence: float = 0.5  # below this, findings are marked uncertain


@dataclass
class RiskFinding:
    rule_id: str
    clause_type: str
    severity: str
    weight: int
    reason: str
    evidence: str = ""
    confidence: float = 0.0
    uncertain: bool = False  # True -> excluded from the score
    explanation: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "clause_type": self.clause_type,
            "severity": self.severity,
            "weight": self.weight,
            "reason": self.reason,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 4),
            "uncertain": self.uncertain,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
        }


@dataclass
class RiskResult:
    overall_score: int  # 0-100, deterministic
    overall_level: str  # LOW / MEDIUM / HIGH
    findings: list[RiskFinding] = field(default_factory=list)
    methodology: str = (
        "Heuristic keyword/presence rules applied to AI-extracted clauses. "
        "Scores are not legal advice; AI confidence and risk severity are "
        "reported separately and never combined."
    )
    bands: dict = field(default_factory=lambda: {"low_max": 30, "medium_max": 60})

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "overall_level": self.overall_level,
            "bands": self.bands,
            "methodology": self.methodology,
            "findings": [f.to_dict() for f in self.findings],
        }
