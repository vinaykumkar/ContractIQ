# Third-Party Notices

ContractIQ depends on the following third-party components. Each keeps its own
license; licenses listed here were verified from the project's package metadata
or the vendor's repository at packaging time.

## Dataset

| Component | License | Notes |
|---|---|---|
| [CUAD v1](https://www.atticusprojectai.org/cuad) (Contract Understanding Atticus Dataset) | CC-BY-4.0 | 510 contracts, 41 clause categories; used for training/evaluation only |

## Bundled model

| Component | License | Notes |
|---|---|---|
| [deepset/minilm-uncased-squad2](https://huggingface.co/deepset/minilm-uncased-squad2) (base of the fine-tuned model) | CC-BY-4.0 | Bundled fine-tuned weights in `ml/models/final/` are a derivative — CC-BY-4.0 permits redistribution with attribution (this file and `docs/ML_MODEL.md` serve as attribution) |

## Major Python libraries

| Component | License |
|---|---|
| PyTorch | BSD-3-Clause |
| Transformers | Apache-2.0 |
| FastAPI | MIT |
| Uvicorn | BSD-3-Clause |
| SQLAlchemy | MIT |
| PyMuPDF | AGPL-3.0 / commercial dual-license (see note) |
| python-docx | MIT |
| scikit-learn | BSD-3-Clause |
| psutil | BSD-3-Clause |
| pytest | MIT |

> **PyMuPDF note:** PyMuPDF is dual-licensed (AGPL-3.0 or commercial). For
> non-commercial/educational use of this project the AGPL terms apply; review
> them if you redistribute this project commercially.

## Frontend libraries

| Component | License |
|---|---|
| React / React DOM | MIT |
| React Router | MIT |
| Tailwind CSS | MIT |
| Framer Motion | MIT |
| Lucide | ISC |
| Vite | MIT |
| TypeScript | Apache-2.0 |
| ESLint / vitest / testing-library | MIT |

## Tools used during development only

Playwright (Apache-2.0) — browser verification scripts; not part of the app bundle.
