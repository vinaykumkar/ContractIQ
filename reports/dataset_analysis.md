# ContractIQ — CUAD Dataset Analysis

_Generated: 2026-08-30T13:50:55.475596+00:00_ · Token counting: `distilbert-base-uncased` · CUDA available: `False`

## 1. Files & split

| File | Contracts | QAs | Categories |
|---|---:|---:|---:|
| CUADv1.json | 510 | 20,910 | 41 |
| train_separate_questions.json | 408 | 22,450 | 41 |
| test.json | 102 | 4,182 | 41 |

Train (408) + test (102) contracts exactly partition the 510 contracts of CUADv1.json: **True**. test.json ships gold answers and is the honest evaluation set; CUADv1.json is the merged superset; train_separate_questions.json explodes each annotated span into its own QA instance (`Category_N` ids).

## 2. Contract length distribution

| File | Metric | min | p25 | median | mean | p75 | p90 | p95 | p99 | max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CUADv1.json | tokens | 172 | 3,338 | 6,736 | 10,841.5 | 13,547 | 24,848 | 35,681 | 60,094 | 78,591 |
| train_separate_questions.json | tokens | 224 | 3,452 | 7,301 | 11,146.6 | 14,052 | 25,764 | 35,681 | 60,094 | 78,591 |
| test.json | tokens | 172 | 2,949 | 5,106 | 9,621.1 | 12,977 | 22,169 | 31,063 | 54,619 | 61,674 |

Longest contracts (tokens):

- CERES,INC_01_25_2012-EX-10.20-Collaboration Agreement — 78,591 tokens (335,282 chars)
- MANUFACTURERSSERVICESLTD_06_05_2000-EX-10.14-OUTSOURCING AGREEMENT — 71,266 tokens (338,211 chars)
- PhasebioPharmaceuticalsInc_20200330_10-K_EX-10.21_12086810_EX-10.21_Development Agreement — 63,425 tokens (291,873 chars)
- VerizonAbsLlc_20200123_8-K_EX-10.4_11952335_EX-10.4_Service Agreement — 61,826 tokens (289,615 chars)
- GOOSEHEADINSURANCE,INC_04_02_2018-EX-10.6-Franchise Agreement — 61,674 tokens (300,768 chars)

## 3. Clause categories

Positivity = share of QA pairs with at least one annotated span (CUADv1 file). Categories sorted by positive count.

| Category | QAs | Positive | No-answer | Positivity | Train+ inst. | Test+ inst. |
|---|---:|---:|---:|---:|---:|---:|
| Document Name | 510 | 510 | 0 | 100.0% | 419 | 102 |
| Parties | 510 | 509 | 1 | 99.8% | 2011 | 102 |
| Agreement Date | 510 | 470 | 40 | 92.2% | 383 | 93 |
| Governing Law | 510 | 437 | 73 | 85.7% | 374 | 83 |
| Expiration Date | 510 | 413 | 97 | 81.0% | 384 | 78 |
| Effective Date | 510 | 390 | 120 | 76.5% | 363 | 70 |
| Anti-Assignment | 510 | 374 | 136 | 73.3% | 517 | 72 |
| Cap On Liability | 510 | 275 | 235 | 53.9% | 554 | 44 |
| License Grant | 510 | 255 | 255 | 50.0% | 642 | 50 |
| Audit Rights | 510 | 214 | 296 | 42.0% | 538 | 38 |
| Termination For Convenience | 510 | 183 | 327 | 35.9% | 205 | 29 |
| Post-Termination Services | 510 | 182 | 328 | 35.7% | 368 | 29 |
| Exclusivity | 510 | 180 | 330 | 35.3% | 332 | 33 |
| Renewal Term | 510 | 176 | 334 | 34.5% | 179 | 26 |
| Insurance | 510 | 166 | 344 | 32.6% | 443 | 32 |
| Revenue/Profit Sharing | 510 | 166 | 344 | 32.6% | 331 | 35 |
| Minimum Commitment | 510 | 165 | 345 | 32.4% | 336 | 32 |
| Non-Transferable License | 510 | 138 | 372 | 27.1% | 255 | 22 |
| Ip Ownership Assignment | 510 | 124 | 386 | 24.3% | 257 | 23 |
| Change Of Control | 510 | 121 | 389 | 23.7% | 191 | 26 |
| Non-Compete | 510 | 119 | 391 | 23.3% | 200 | 23 |
| Notice Period To Terminate Renewal | 510 | 111 | 399 | 21.8% | 104 | 16 |
| Uncapped Liability | 510 | 111 | 399 | 21.8% | 151 | 13 |
| Covenant Not To Sue | 510 | 100 | 410 | 19.6% | 129 | 24 |
| Rofr/Rofo/Rofn | 510 | 85 | 425 | 16.7% | 299 | 17 |
| Volume Restriction | 510 | 82 | 428 | 16.1% | 136 | 17 |
| Competitive Restriction Exception | 510 | 76 | 434 | 14.9% | 98 | 16 |
| Warranty Duration | 510 | 75 | 435 | 14.7% | 157 | 10 |
| Irrevocable Or Perpetual License | 510 | 70 | 440 | 13.7% | 142 | 13 |
| Liquidated Damages | 510 | 61 | 449 | 12.0% | 98 | 14 |
| Affiliate License-Licensee | 510 | 59 | 451 | 11.6% | 88 | 12 |
| No-Solicit Of Employees | 510 | 59 | 451 | 11.6% | 73 | 10 |
| Joint Ip Ownership | 510 | 46 | 464 | 9.0% | 101 | 7 |
| Non-Disparagement | 510 | 38 | 472 | 7.4% | 53 | 7 |
| No-Solicit Of Customers | 510 | 34 | 476 | 6.7% | 43 | 7 |
| Third Party Beneficiary | 510 | 32 | 478 | 6.3% | 28 | 6 |
| Most Favored Nation | 510 | 28 | 482 | 5.5% | 35 | 3 |
| Affiliate License-Licensor | 510 | 23 | 487 | 4.5% | 49 | 6 |
| Unlimited/All-You-Can-Eat-License | 510 | 17 | 493 | 3.3% | 26 | 3 |
| Price Restrictions | 510 | 15 | 495 | 2.9% | 27 | 0 |
| Source Code Escrow | 510 | 13 | 497 | 2.5% | 61 | 1 |

## 4. Version-1 enabled clauses (15)

| Label | CUAD category | Question tokens (median) | Train windows | Test windows |
|---|---|---:|---:|---:|
| `document_name` | Document Name | 31 | 34,614 | 7,440 |
| `parties` | Parties | 34 | 34,622 | 7,442 |
| `agreement_date` | Agreement Date | 31 | 34,614 | 7,440 |
| `effective_date` | Effective Date | 33 | 34,616 | 7,441 |
| `expiration_date` | Expiration Date | 40 | 34,655 | 7,448 |
| `renewal_term` | Renewal Term | 53 | 34,697 | 7,459 |
| `governing_law` | Governing Law | 41 | 34,664 | 7,448 |
| `termination_for_convenience` | Termination For Convenience | 51 | 34,693 | 7,458 |
| `non_compete` | Non-Compete | 55 | 34,700 | 7,462 |
| `exclusivity` | Exclusivity | 103 | 34,842 | 7,501 |
| `anti_assignment` | Anti-Assignment | 45 | 34,678 | 7,453 |
| `license_grant` | License Grant | 41 | 34,664 | 7,448 |
| `audit_rights` | Audit Rights | 53 | 34,697 | 7,459 |
| `cap_on_liability` | Cap On Liability | 62 | 34,728 | 7,464 |
| `insurance` | Insurance | 46 | 34,681 | 7,455 |

Total sliding-window chunks at max_seq_len=512, stride=128: **520,165** train / **111,818** test.

## 5. Data quality

| Check | CUADv1 | train | test |
|---|---:|---:|---:|
| missing_fields | 0 | 0 | 0 |
| empty_context | 0 | 0 | 0 |
| answer_out_of_bounds | 0 | 0 | 0 |
| answer_text_mismatch | 0 | 0 | 0 |
| answer_text_mismatch_normalized | 0 | 0 | 0 |
| impossible_with_answers | 0 | 0 | 0 |
| possible_without_answers | 0 | 0 | 0 |
| duplicate_qa_ids | 0 | 0 | 0 |
| duplicate_contract_titles | 0 | 0 | 0 |
| category_parse_failures | 0 | 0 | 0 |

## 6. Notes for modelling

- Category imbalance is strong (see Positivity column): head categories such as `Document Name` or `Governing Law` are positive in nearly every contract; several tail categories sit below 10%. Use per-category metrics and no-answer-aware evaluation.
- Training should consume `train_separate_questions.json` (one QA instance per annotated span); evaluation should use `test.json` and deduplicate spans per category.
- Gold answers may differ from the raw context slice by whitespace; exact and normalized mismatch counters are reported above and preprocessing must tolerate this.
- These statistics describe the dataset only. AI-assisted analysis; results should be reviewed by a qualified professional.