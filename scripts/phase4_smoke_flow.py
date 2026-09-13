#!/usr/bin/env python
"""Phase 4 local smoke flow (no API): real end-to-end integration proof.

    synthetic sample document
    -> file safety + document parser (DOCX, generated locally)
    -> ML adapter (the REAL fine-tuned model, one short contract = a few seconds)
    -> heuristic risk engine
    -> SQLite persistence (project-relative storage/contractiq.db)
    -> reload saved analysis from the database and verify

Writes reports/phase4_smoke_flow.json. Runtime: a few seconds (one analysis).
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

SAMPLE = """MASTER SERVICES AGREEMENT (SHORT DEMO)

This Master Services Agreement is entered into as of January 15, 2025 by and
between DemoCo Inc., a company organized under the laws of Delaware, and
Supplier Ltd.

1. TERM AND RENEWAL. The initial term is one (1) year and this agreement shall
automatically renew for successive one-year terms unless either party gives
sixty (60) days written notice of non-renewal.

2. NON-COMPETE. Supplier shall not compete with DemoCo in the field of
office supplies during the term.

3. TERMINATION. DemoCo may terminate this agreement for convenience upon
thirty (30) days prior written notice.

4. GOVERNING LAW. This agreement is governed by the laws of the State of
California.
"""


def main() -> int:
    from app.core.config import load_settings
    from app.services.contract_analysis import ContractAnalysisService
    from app.services.ml_adapter import MLAnalyzerAdapter
    from app.utils.files import save_upload

    steps: dict = {}
    t0 = time.perf_counter()

    # 1. build a synthetic DOCX (as an uploader would submit)
    import docx

    d = docx.Document()
    for para in SAMPLE.split("\n\n"):
        d.add_paragraph(para)
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "demo.docx"
        d.save(str(raw))
        content = raw.read_bytes()

    # 2. file safety + storage (generated internal id)
    settings = load_settings()
    stored_path, internal_id, display_name = save_upload(content, "../../evil/../demo msA.docx", settings)
    steps["file_safety"] = {"display_name": display_name, "internal_id": internal_id,
                            "stored": str(stored_path.relative_to(PROJECT_ROOT))}
    print(f"[1] file safety: '{display_name}' stored as {internal_id}.docx")

    # 3. parse
    service = ContractAnalysisService(analyzer=MLAnalyzerAdapter(settings.ml_model_config),
                                      settings=settings)
    ing = service.ingest_document(stored_path, display_name)
    steps["parsing"] = {k: ing[k] for k in ("file_type", "character_count", "page_count", "warnings")}
    print(f"[2] parsed: {ing['file_type']}, {ing['character_count']} chars, "
          f"duplicate_of={ing['duplicate_of']}")

    # 4. analyze with the REAL fine-tuned model + risk engine + persistence
    result = service.analyze_contract(ing["contract_id"])
    a = result["analysis"]
    print(f"[3] analyzed: model_state={a['model_state']} version={a['model_version']} "
          f"in {a['processing_ms']:.0f} ms")
    print(f"    risk: {a['overall_risk_score']} ({a['overall_risk_level']})")
    found = [c for c in result["clauses"] if c["found"]]
    for c in found:
        print(f"    found {c['clause_type']}: conf={c['confidence']} "
              f"risk={c['risk_level']} text={c['text'][:60]!r}")
    steps["analysis"] = {
        "model_state": a["model_state"], "model_version": a["model_version"],
        "processing_ms": a["processing_ms"],
        "overall_risk_score": a["overall_risk_score"], "overall_risk_level": a["overall_risk_level"],
        "clauses_found": [c["clause_type"] for c in found],
        "rule_ids": sorted({f["rule_id"] for f in result["risk_findings"]}),
    }

    # 5. reload everything from the database and verify
    reloaded = service.get_full_result(ing["contract_id"])
    assert reloaded is not None
    assert reloaded["analysis"]["status"] == "COMPLETED"
    assert reloaded["analysis"]["overall_risk_score"] == a["overall_risk_score"]
    assert len(reloaded["clauses"]) == len(result["clauses"])
    assert reloaded["contract"]["text"].startswith("MASTER SERVICES AGREEMENT")
    # evidence substring property
    for c in reloaded["clauses"]:
        if c["found"]:
            assert reloaded["contract"]["text"][c["start_char"]:c["end_char"]] == c["text"]
    steps["persistence"] = {"status": reloaded["analysis"]["status"],
                            "clause_rows": len(reloaded["clauses"]),
                            "finding_rows": len(reloaded["risk_findings"]),
                            "evidence_substring_check": True}
    print(f"[4] reloaded from SQLite: {steps['persistence']}")

    from app.db.database import get_engine
    from app.db import repository as repo
    from app.db.database import make_session_factory, session_scope

    factory = make_session_factory(get_engine(settings.database_url))
    with session_scope(factory) as s:
        steps["stats"] = repo.stats_summary(s)
    print(f"[5] db stats: {steps['stats']}")

    steps["total_seconds"] = round(time.perf_counter() - t0, 1)
    out = PROJECT_ROOT / "reports" / "phase4_smoke_flow.json"
    out.write_text(json.dumps(steps, indent=2), encoding="utf-8")
    print(f"\nSMOKE FLOW PASSED in {steps['total_seconds']}s -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
