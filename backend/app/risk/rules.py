"""Version-1 heuristic risk rules for the 15 enabled clauses.

Principles (see docs/RISK_ENGINE.md):
- CUAD has no trustworthy legal risk labels, so every rule is a transparent,
  conservative heuristic; nothing here is legal advice.
- Weights are small and capped; absence-of-protection rules weigh less than
  presence-of-restriction rules.
- Informational rules (weight 0) exist for traceability, not scoring.
"""
from __future__ import annotations

from .models import RiskRule

RISK_RULES: list[RiskRule] = [
    # ---- restrictive obligations (presence) ----
    RiskRule(
        rule_id="NON_COMPETE_PRESENT",
        clause_label="non_compete",
        trigger="present",
        weight=18,
        severity="HIGH",
        reason="Restrictive non-compete language detected.",
        explanation="A non-compete clause restricts a party's freedom to engage in "
                    "competing business during or after the contract.",
        recommendation="Review scope, duration and geography of the restriction.",
    ),
    RiskRule(
        rule_id="EXCLUSIVITY_PRESENT",
        clause_label="exclusivity",
        trigger="present",
        weight=15,
        severity="HIGH",
        reason="Exclusivity obligation detected.",
        explanation="Exclusivity limits a party from dealing with other counterparties.",
        recommendation="Confirm the exclusivity scope is intentional and commercially acceptable.",
    ),
    # ---- renewal ----
    RiskRule(
        rule_id="AUTO_RENEWAL_LANGUAGE",
        clause_label="renewal_term",
        trigger="wording",
        weight=10,
        severity="MEDIUM",
        reason="Automatic renewal (evergreen) language detected.",
        explanation="The contract may renew automatically unless notice is given, "
                    "which can extend obligations unintentionally.",
        recommendation="Diarise the non-renewal notice deadline.",
        wording_pattern=r"(?i)automatic(ally)?\s+renew|auto\s*-\s*renew|autorenew|evergreen|renewed\s+automatically",
    ),
    RiskRule(
        rule_id="RENEWAL_TERM_PRESENT",
        clause_label="renewal_term",
        trigger="present",
        weight=5,
        severity="LOW",
        reason="Renewal term clause detected.",
        explanation="The contract defines how it is renewed.",
        recommendation="Check renewal notice periods.",
    ),
    # ---- assignment ----
    RiskRule(
        rule_id="ANTI_ASSIGNMENT_RESTRICTIVE",
        clause_label="anti_assignment",
        trigger="wording",
        weight=8,
        severity="MEDIUM",
        reason="Anti-assignment clause restricts transferring the contract.",
        explanation="Assignment typically requires counterparty consent, "
                    "limiting M&A or restructuring flexibility.",
        recommendation="Check whether consent can be unreasonably withheld.",
        wording_pattern=r"(?i)without\s+(the\s+)?prior\s+written\s+consent|shall\s+not\s+(be\s+)?assign",
    ),
    RiskRule(
        rule_id="ANTI_ASSIGNMENT_PRESENT",
        clause_label="anti_assignment",
        trigger="present",
        weight=3,
        severity="LOW",
        reason="Anti-assignment clause detected.",
        explanation="The contract addresses assignment of rights or obligations.",
    ),
    # ---- missing protections (absence) ----
    RiskRule(
        rule_id="TERMINATION_CONVENIENCE_ABSENT",
        clause_label="termination_for_convenience",
        trigger="absent",
        weight=10,
        severity="MEDIUM",
        reason="No termination-for-convenience clause found.",
        explanation="Without it, exiting the contract early may be difficult or costly.",
        recommendation="Consider negotiating a termination right.",
    ),
    RiskRule(
        rule_id="CAP_ON_LIABILITY_ABSENT",
        clause_label="cap_on_liability",
        trigger="absent",
        weight=12,
        severity="MEDIUM",
        reason="No cap on liability found.",
        explanation="Liability may be uncapped, exposing parties to unlimited damages.",
        recommendation="Consider negotiating a liability cap.",
    ),
    # ---- informational / low ----
    RiskRule(
        rule_id="INSURANCE_REQUIREMENT_PRESENT",
        clause_label="insurance",
        trigger="present",
        weight=4,
        severity="LOW",
        reason="Insurance requirement detected.",
        explanation="One party must maintain specified insurance coverage.",
    ),
    RiskRule(
        rule_id="AUDIT_RIGHTS_PRESENT",
        clause_label="audit_rights",
        trigger="present",
        weight=4,
        severity="LOW",
        reason="Audit rights clause detected.",
        explanation="A party may inspect the other party's relevant records.",
    ),
    RiskRule(
        rule_id="GOVERNING_LAW_PRESENT",
        clause_label="governing_law",
        trigger="present",
        weight=0,
        severity="INFO",
        reason="Governing law clause detected.",
        explanation="Identifies the jurisdiction whose law applies.",
    ),
    RiskRule(
        rule_id="LICENSE_GRANT_PRESENT",
        clause_label="license_grant",
        trigger="present",
        weight=0,
        severity="INFO",
        reason="License grant detected.",
        explanation="The contract grants rights to use intellectual property.",
    ),
    RiskRule(
        rule_id="PARTIES_IDENTIFIED",
        clause_label="parties",
        trigger="present",
        weight=0,
        severity="INFO",
        reason="Contract parties identified.",
        explanation="Traceability: parties extracted for the summary.",
    ),
    RiskRule(
        rule_id="AGREEMENT_DATE_IDENTIFIED",
        clause_label="agreement_date",
        trigger="present",
        weight=0,
        severity="INFO",
        reason="Agreement date identified.",
        explanation="Traceability: date extracted for the summary.",
    ),
]


def rules_for(clause_label: str) -> list[RiskRule]:
    return [r for r in RISK_RULES if r.clause_label == clause_label]
