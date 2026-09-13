# Demo Contracts

Twenty-seven ready-to-upload sample agreements for presentations and testing
(22 agreements; 5 also as PDF). **This folder is presentation material only —
the application never reads it, and nothing here was uploaded to the app.**
Uploading happens only when you drag a file into the app yourself.

## The files

| File | Type | Intended risk story |
|---|---|---|
| 01_saas_subscription_low_risk (.docx + .pdf) | SaaS subscription | friendly terms, no lock-in → LOW |
| 02_mutual_nda_low_risk.docx | Mutual NDA | minimal obligations → LOW |
| 03_freelance_contractor_low_risk.docx | Freelance engagement | short term, easy exit → LOW |
| 04_commercial_lease_medium_risk.docx | Commercial lease | auto-renewal + assignment limits → MEDIUM |
| 05_consulting_services_medium_risk.docx | Consulting services | auto-renewal + soft non-compete → MEDIUM |
| 06_supply_vendor_medium_risk.docx | Exclusive supply | exclusivity + auto-renewal → MEDIUM |
| 07_employment_agreement_high_risk (.docx + .pdf) | Executive employment | non-compete + no convenience exit → HIGH |
| 08_distribution_agreement_high_risk.docx | Exclusive distribution | non-compete + minimums + auto-renewal → HIGH |
| 09_franchise_agreement_high_risk (.docx + .pdf) | Franchise | heavy lock-in across many rules → HIGH |
| 10_partnership_llc_medium_risk.docx | LLC operating agreement | member restraints → MEDIUM |
| 11_loan_agreement_low_risk.docx | Loan / promissory note | standard bank terms → LOW |
| 12_software_license_medium_risk.docx | Enterprise software license | auto-renewal + audit → MEDIUM |
| 13_joint_venture_agreement_high_risk (.docx + .pdf) | Joint venture | non-compete + tech exclusivity → HIGH |
| 14_reseller_agreement_low_risk.docx | Non-exclusive reseller | easy exit, no lock-in → LOW |
| 15_real_estate_purchase_agreement_low_risk.docx | Real-estate purchase | one-shot deal, deposit cap → LOW |
| 16_influencer_creator_agreement_medium_risk.docx | Content creator / influencer | category exclusivity + auto-renewal → MEDIUM |
| 17_manufacturing_agreement_medium_risk.docx | Toll manufacturing | auto-renewal + capacity commit → MEDIUM |
| 18_research_collaboration_low_risk.docx | University research collab | academic terms → LOW |
| 19_equipment_rental_agreement_medium_risk.docx | Equipment rental | auto-renewal + no cap → MEDIUM |
| 20_data_processing_agreement_low_risk.docx | GDPR data processing | protective, capped → LOW |
| 21_sponsorship_agreement_high_risk (.docx + .pdf) | Event sponsorship | category exclusivity + no exit → HIGH |
| 22_logistics_services_agreement_medium_risk.docx | Logistics & warehousing | auto-renewal + low liability cap → MEDIUM |

The "intended risk story" is a demo guide, not a promise — ContractIQ computes
the real score from its own rules, and showing the engine disagree with the
label is a perfectly good talking point.

## Demo tips

- Upload the `.docx` files normally; the three `.pdf` files exist so you can
  also demonstrate PDF parsing.
- Good 3-minute flow: analyze **01 (LOW)**, then **05 (MEDIUM)**, then
  **09 (HIGH)** — the Risk Orb, risk findings and evidence highlighting change
  visibly between them.
- Everything runs locally; nothing in these files leaves your machine.

## Regenerating

The files are produced by `generate_demo_contracts.py` in this folder:

```
..\.venv\Scripts\python.exe generate_demo_contracts.py
```

Edit the templates in that script to add more agreements, then re-run it.
Safe to delete this entire folder at any time — the project does not depend
on it.
