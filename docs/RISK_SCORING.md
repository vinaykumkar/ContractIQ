# ContractIQ — Risk Scoring

> ContractIQ provides AI-assisted contract analysis and is not a substitute for
> professional legal advice. The risk score is a transparent heuristic — it is
> not a legal opinion.

## Principle

CUAD provides **no legal risk labels**, so risk scoring is deliberately
separated from the AI model: the model only extracts clauses with confidence;
a deterministic rule engine converts those findings into a score. ML
confidence and risk severity are reported side by side and never merged.

## Bands

| Score | Level |
|---|---|
| 0–30 | LOW |
| 31–60 | MEDIUM |
| 61–100 | HIGH |

Bands are configurable in `ml/configs/clauses.json` (`risk_bands`).

## Rules (15, all in `backend/app/risk/rules.py`)

| Rule | Clause | Trigger | Weight | Severity |
|---|---|---|---:|---|
| NON_COMPETE_PRESENT | non_compete | present | 18 | HIGH |
| EXCLUSIVITY_PRESENT | exclusivity | present | 15 | HIGH |
| AUTO_RENEWAL_LANGUAGE | renewal_term | wording | 10 | MEDIUM |
| RENEWAL_TERM_PRESENT | renewal_term | present | 5 | LOW |
| ANTI_ASSIGNMENT_RESTRICTIVE | anti_assignment | wording | 8 | MEDIUM |
| ANTI_ASSIGNMENT_PRESENT | anti_assignment | present | 3 | LOW |
| TERMINATION_CONVENIENCE_ABSENT | termination_for_convenience | absent | 10 | MEDIUM |
| CAP_ON_LIABILITY_ABSENT | cap_on_liability | absent | 12 | MEDIUM |
| INSURANCE_REQUIREMENT_PRESENT | insurance | present | 4 | LOW |
| AUDIT_RIGHTS_PRESENT | audit_rights | present | 4 | LOW |
| GOVERNING_LAW / LICENSE_GRANT / PARTIES / AGREEMENT_DATE | … | present | 0 | INFO |

- **present** rules fire when the clause was found with confidence ≥ 0.5
  (configurable `CONTRACTIQ_RISK_MIN_CONFIDENCE`).
- **wording** rules additionally require a regex match in the extracted text
  (e.g. automatic-renewal or "without prior written consent" language).
- **absent** rules fire when the clause was not found.
- Weight-0 rules are informational (traceability), never scored.

## Confidence-aware behaviour

If a clause is found but ML confidence is below the rule threshold, the
finding is shown as **uncertain** ("low ML confidence — not scored") and is
excluded from the score. The model's confidence number and the rule's severity
are displayed separately.

## Determinism

`evaluate_risk()` is a pure function: identical clause results always produce
an identical score, level and findings. Score = sum of weights of certain
findings, capped at 100.
