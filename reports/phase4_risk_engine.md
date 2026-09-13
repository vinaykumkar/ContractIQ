# ContractIQ — Phase 4 Risk Engine Report

_Generated: 2026-08-31 · Verified by `backend/tests/test_risk_engine.py` (13 tests) and the Phase 4 smoke flow._

## Principle

CUAD provides no trustworthy legal risk labels. Risk scoring is therefore a
**transparent, deterministic, configurable heuristic layer** that consumes the
ML clause findings — never a legal conclusion, and never blended with ML
confidence. Every result carries the disclaimer: *"AI-assisted analysis.
Results should be reviewed by a qualified professional."*

## Rule inventory (15 rules over the 15 enabled clauses)

| Rule ID | Clause | Trigger | Weight | Severity |
|---|---|---|---:|---|
| NON_COMPETE_PRESENT | non_compete | present | 18 | HIGH |
| EXCLUSIVITY_PRESENT | exclusivity | present | 15 | HIGH |
| AUTO_RENEWAL_LANGUAGE | renewal_term | wording regex | 10 | MEDIUM |
| RENEWAL_TERM_PRESENT | renewal_term | present | 5 | LOW |
| ANTI_ASSIGNMENT_RESTRICTIVE | anti_assignment | wording regex | 8 | MEDIUM |
| ANTI_ASSIGNMENT_PRESENT | anti_assignment | present | 3 | LOW |
| TERMINATION_CONVENIENCE_ABSENT | termination_for_convenience | absent | 10 | MEDIUM |
| CAP_ON_LIABILITY_ABSENT | cap_on_liability | absent | 12 | MEDIUM |
| INSURANCE_REQUIREMENT_PRESENT | insurance | present | 4 | LOW |
| AUDIT_RIGHTS_PRESENT | audit_rights | present | 4 | LOW |
| GOVERNING_LAW_PRESENT | governing_law | present | 0 | INFO |
| LICENSE_GRANT_PRESENT | license_grant | present | 0 | INFO |
| PARTIES_IDENTIFIED | parties | present | 0 | INFO |
| AGREEMENT_DATE_IDENTIFIED | agreement_date | present | 0 | INFO |

Rules live in `backend/app/risk/rules.py` with `rule_id, clause_label, trigger, weight, severity, reason, explanation, recommendation, wording_pattern, min_confidence`.

## Scoring method (deterministic)

1. `absent` rules fire when the ML layer reports `found=false` (no confidence involved).
2. `present`/`wording` rules fire only on `found=true` (wording rules additionally require the regex to match the extracted text).
3. **Confidence-awareness:** if the clause was found but ML confidence < the rule's `min_confidence` (default 0.5, env `CONTRACTIQ_RISK_MIN_CONFIDENCE`), the finding is emitted **uncertain** — shown to the user with its reason, but weight 0 in the score. ML confidence and legal severity are reported side by side, never merged.
4. Score = sum of weights of certain findings, capped at 100.
5. Bands (read from `ml/configs/clauses.json`): **0–30 LOW · 31–60 MEDIUM · 61–100 HIGH**.

Same input → same output, always (asserted by `test_deterministic`).

## Measured behaviour

- Baseline all-absent analysis scores 22 (two absence rules) — LOW band.
- Smoke-flow demo contract (real model): non-compete 18 + auto-renewal 10 + renewal 5 + cap-absent 12 = **45 → MEDIUM**, with per-clause levels (non_compete HIGH, renewal MEDIUM, governing_law INFO) and evidence snippets persisted.
- Band boundaries verified: 22→LOW, 55→MEDIUM, 70→HIGH.
- All rule weights ≤ 25; five-caps-scenario confirms the 100-point cap.
