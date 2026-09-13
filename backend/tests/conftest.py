"""Backend test fixtures: path bootstrap, settings, synthetic documents.

Synthetic test documents are generated programmatically (tiny TXT/DOCX/PDF),
never copied from CUAD. The ML analyzer is mocked everywhere except one
explicitly-marked real smoke test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_SRC = PROJECT_ROOT / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.core.config import Settings  # noqa: E402

SAMPLE_CONTRACT_TEXT = """DISTRIBUTION AGREEMENT

This Distribution Agreement is made by and between Alpha Corp, a Delaware
corporation, and Beta LLC, effective as of March 1, 2025.

1. TERM. The initial term is two (2) years and shall automatically renew for
successive one (1) year periods unless notice of non-renewal is given.

2. EXCLUSIVITY. Distributor shall sell the products exclusively in the
territory and shall not distribute competing products.

3. NON-COMPETE. For twelve (12) months after termination, Distributor shall
not compete with the Company in any market.

4. ASSIGNMENT. Neither party may assign this Agreement without the prior
written consent of the other party.

5. TERMINATION. Either party may terminate this Agreement for convenience
upon ninety (90) days written notice.

6. LIABILITY. In no event shall Company's aggregate liability exceed the
fees paid in the prior twelve (12) months.

7. GOVERNING LAW. This Agreement is governed by the laws of the State of
New York.

8. INSURANCE. Distributor shall maintain commercial insurance coverage of
at least one million dollars.
"""


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    """Isolated settings per test: tmp storage dirs + tmp SQLite file."""
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        upload_dir=tmp_path / "uploads",
        temp_dir=tmp_path / "temp",
    )


@pytest.fixture()
def sample_txt(tmp_path: Path) -> Path:
    p = tmp_path / "sample contract.txt"
    with p.open("w", encoding="utf-8", newline="\n") as f:
        f.write(SAMPLE_CONTRACT_TEXT)
    return p


@pytest.fixture()
def sample_docx(tmp_path: Path) -> Path:
    import docx

    d = docx.Document()
    for para in SAMPLE_CONTRACT_TEXT.split("\n\n"):
        d.add_paragraph(para)
    table = d.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Party"
    table.cell(0, 1).text = "Role"
    table.cell(1, 0).text = "Alpha Corp"
    table.cell(1, 1).text = "Company"
    p = tmp_path / "sample_contract.docx"
    d.save(str(p))
    return p


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    """Text PDF generated locally with PyMuPDF (multi-page)."""
    import fitz

    doc = fitz.open()
    for chunk in SAMPLE_CONTRACT_TEXT.split("\n\n")[:6]:
        page = doc.new_page()  # default A5-ish size
        page.insert_text((50, 60), chunk.replace("\n", " ")[:400], fontsize=9)
    p = tmp_path / "sample_contract.pdf"
    doc.save(str(p))
    doc.close()
    return p


@pytest.fixture()
def scanned_pdf(tmp_path: Path) -> Path:
    """Image-only PDF: pages with a drawn rectangle but no text."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.draw_rect(fitz.Rect(50, 50, 300, 300), color=(0, 0, 0), width=1)
    p = tmp_path / "scanned.pdf"
    doc.save(str(p))
    doc.close()
    return p


@pytest.fixture()
def encrypted_pdf(tmp_path: Path) -> Path:
    import fitz

    doc = fitz.open()
    doc.new_page().insert_text((50, 60), "secret text", fontsize=10)
    p = tmp_path / "encrypted.pdf"
    doc.save(str(p), encryption=fitz.PDF_ENCRYPT_AES_128, user_pw="pw", owner_pw="pw")
    doc.close()
    return p


@pytest.fixture()
def corrupt_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "corrupt.pdf"
    p.write_bytes(b"%PDF-1.4 this is not really a pdf \x00\x01\x02 broken")
    return p


class MockAnalyzer:
    """Deterministic stand-in for the Phase 3 analyzer (no transformer)."""

    def __init__(self, findings: dict[str, dict] | None = None, fail: bool = False):
        self.fail = fail
        self._findings = findings or {
            "governing_law": {"found": True, "text": "laws of the State of New York",
                              "confidence": 0.92, "start_char": 700, "end_char": 728},
            "non_compete": {"found": True, "text": "shall not compete with the Company",
                            "confidence": 0.88, "start_char": 400, "end_char": 434},
            "exclusivity": {"found": True, "text": "exclusively in the territory",
                            "confidence": 0.81, "start_char": 300, "end_char": 328},
            "renewal_term": {"found": True, "text": "automatically renew for successive one (1) year",
                             "confidence": 0.77, "start_char": 200, "end_char": 249},
            "anti_assignment": {"found": True, "text": "without the prior written consent",
                                "confidence": 0.74, "start_char": 500, "end_char": 532},
            "termination_for_convenience": {"found": False, "text": "", "confidence": 0.05,
                                            "start_char": -1, "end_char": -1},
            "cap_on_liability": {"found": False, "text": "", "confidence": 0.03,
                                 "start_char": -1, "end_char": -1},
        }

    def analyze_contract(self, text: str, enabled_clauses=None) -> dict:
        if self.fail:
            raise RuntimeError("model exploded")
        labels = enabled_clauses or list(self._findings)
        clauses = []
        for label in labels:
            f = self._findings.get(label, {"found": False, "text": "", "confidence": 0.0,
                                           "start_char": -1, "end_char": -1})
            clauses.append({"clause_type": label, **f, "question": "",
                            "model_state": "fine_tuned", "model_version": "test",
                            "processing_ms": 1.0})
        return {"clauses": clauses, "model_state": "fine_tuned",
                "model_version": "test", "total_processing_ms": 1.0}

    def analyze_clause(self, text: str, clause_label: str) -> dict:
        return self.analyze_contract(text, [clause_label])["clauses"][0]


@pytest.fixture()
def mock_analyzer():
    return MockAnalyzer()
