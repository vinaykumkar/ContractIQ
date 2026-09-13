# ContractIQ — Phase 2 Preprocessing Report

_Generated: 2026-08-30T14:29:02.480351+00:00_

## Split & leakage

- Deterministic contract-level split: **367 train / 41 val** (seed=42, val_fraction=0.1) carved only from the 408 official training contracts.
- Official test set: **102 contracts, untouched**.
- Overlaps train∩val=0, train∩test=0, val∩test=0 — all must be 0.

## Features

- Train windows: **183,385** (positive 5,105 / no-answer 178,280 → 2.8% positive)
- Validation eval windows: **22,723**
- Windows per (contract, clause): median 22, max 283

| Clause | CUAD category | Windows | Positive windows |
|---|---|---:|---:|
| `agreement_date` | Agreement Date | 13,050 | 360 |
| `anti_assignment` | Anti-Assignment | 13,577 | 412 |
| `audit_rights` | Audit Rights | 13,905 | 379 |
| `cap_on_liability` | Cap On Liability | 14,296 | 424 |
| `document_name` | Document Name | 13,050 | 392 |
| `effective_date` | Effective Date | 13,126 | 352 |
| `exclusivity` | Exclusivity | 16,375 | 292 |
| `expiration_date` | Expiration Date | 13,383 | 394 |
| `governing_law` | Governing Law | 13,426 | 399 |
| `insurance` | Insurance | 13,619 | 224 |
| `license_grant` | License Grant | 13,426 | 478 |
| `non_compete` | Non-Compete | 13,997 | 167 |
| `parties` | Parties | 13,159 | 473 |
| `renewal_term` | Renewal Term | 13,905 | 168 |
| `termination_for_convenience` | Termination For Convenience | 13,814 | 191 |

## Question token budget

| Clause | Question tokens | Context budget (of 512) | At risk |
|---|---:|---:|---|
| `agreement_date` | 31 | 478 | False |
| `anti_assignment` | 45 | 464 | False |
| `audit_rights` | 53 | 456 | False |
| `cap_on_liability` | 62 | 447 | False |
| `document_name` | 31 | 478 | False |
| `effective_date` | 33 | 476 | False |
| `exclusivity` | 103 | 406 | False |
| `expiration_date` | 40 | 469 | False |
| `governing_law` | 41 | 468 | False |
| `insurance` | 46 | 463 | False |
| `license_grant` | 41 | 468 | False |
| `non_compete` | 55 | 454 | False |
| `parties` | 34 | 475 | False |
| `renewal_term` | 53 | 456 | False |
| `termination_for_convenience` | 51 | 458 | False |

## Data anomalies

- Gold spans cut mid-wordpiece-token: **30** of 4473 unique spans (0.7%). Labels use the containing token (standard); exact char offsets stay in feature metadata.

## Performance

- Preparation wall time: 51s · peak RSS 0.59 GB · 19+3 Parquet shards (10,000 rows each)

## Storage

- `data\processed\train_features` — train features (input_ids, start/end, metadata)
- `data\processed\val_eval_features` — eval features (input_ids, char offsets, metadata)
- `data\processed\split_metadata.json` — reproducible split (ids + seed)

Contract text is NOT duplicated per window; features store token ids and offsets, and everything is reproducible from data/raw/ via this script.