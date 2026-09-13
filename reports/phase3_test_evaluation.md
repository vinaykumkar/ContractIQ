# ContractIQ — Phase 3 Official Test Evaluation

_Generated: 2026-08-30T17:23:48.602611+00:00_ · Run ONCE on the untouched 102-contract test set.

Model: **fine_tuned** (`ml\models\final`) · version `phase3-finetuned-minilm-squad2-1epoch`
Frozen decoding: delta=0.0, min_confidence=0.0

## Overall

| Metric | Value |
|---|---:|
| Overall EM (SQuAD2 convention) | 60.8% |
| Overall F1 | 66.2% |
| Answerable EM (875 pairs) | 50.6% |
| Answerable F1 | 60.2% |
| Answerable precision / recall | 63.2% / 61.2% |
| No-answer accuracy (655 pairs) | 74.4% |
| Answerable-detection recall / found-precision / macro F1 | 83.2% / 81.2% / 82.2% |

## Per-clause

| Clause | Pairs | Answerable | EM | F1 | Answerable F1 | No-answer acc. |
|---|---:|---:|---:|---:|---:|---:|
| agreement_date | 102 | 93 | 73.5% | 77.9% | 82.2% | 33.3% |
| anti_assignment | 102 | 72 | 65.7% | 72.8% | 62.8% | 96.7% |
| audit_rights | 102 | 38 | 64.7% | 70.3% | 44.0% | 85.9% |
| cap_on_liability | 102 | 44 | 50.0% | 57.9% | 43.4% | 69.0% |
| document_name | 102 | 102 | 77.5% | 89.0% | 89.0% | n/a |
| effective_date | 102 | 70 | 48.0% | 52.9% | 68.5% | 18.8% |
| exclusivity | 102 | 33 | 59.8% | 64.5% | 44.9% | 73.9% |
| expiration_date | 102 | 78 | 72.5% | 77.5% | 78.3% | 75.0% |
| governing_law | 102 | 83 | 79.4% | 84.5% | 83.3% | 89.5% |
| insurance | 102 | 32 | 68.6% | 73.9% | 38.5% | 90.0% |
| license_grant | 102 | 50 | 47.1% | 56.1% | 32.4% | 78.8% |
| non_compete | 102 | 23 | 73.5% | 76.1% | 28.8% | 89.9% |
| parties | 102 | 102 | 8.8% | 13.7% | 13.7% | n/a |
| renewal_term | 102 | 26 | 52.9% | 55.5% | 56.2% | 55.3% |
| termination_for_convenience | 102 | 29 | 69.6% | 71.1% | 74.1% | 69.9% |

Runtime: 412s model time · avg 230.4 windows/contract (with frozen retrieval).
