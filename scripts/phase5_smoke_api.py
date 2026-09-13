#!/usr/bin/env python
"""Phase 5 real API integration smoke test (ONE small run, no mocks).

tiny TXT contract -> POST /api/contracts/upload (real parser)
                  -> POST /api/contracts/{id}/analyze (REAL fine-tuned model)
                  -> GET /api/contracts/{id}/analysis (risk, clauses, entities)
                  -> GET /api/contracts/{id}/text + /api/stats + /docs + /openapi.json

Uses its own temp SQLite DB (never the demo database) and a very short
contract. Writes reports/phase5_smoke_api.json and prints simple timings.
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

TINY_CONTRACT = """CONSULTING AGREEMENT

This Consulting Agreement is made as of February 1, 2025 between Innotech Ltd
and advisor Jane Doe.

1. TERM. This agreement runs for six months and shall automatically renew
unless terminated with 30 days notice.

2. TERMINATION. Either party may terminate this agreement for convenience
upon fourteen (14) days written notice.

3. GOVERNING LAW. This agreement is governed by the laws of the State of
Texas.
"""


def main() -> int:
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        settings = Settings(
            database_url=f"sqlite:///{(tmp / 'smoke-api.db').as_posix()}",
            upload_dir=tmp / "uploads",
            temp_dir=tmp / "temp",
        )
        app = create_app(settings)
        results: dict = {"steps": {}, "timings_ms": {}}

        with TestClient(app) as client:
            # OpenAPI/docs availability
            t0 = time.perf_counter()
            assert client.get("/openapi.json").status_code == 200
            assert client.get("/docs").status_code == 200
            assert client.get("/redoc").status_code == 200
            spec = client.get("/openapi.json").json()
            results["openapi_paths"] = sorted(spec["paths"].keys())
            results["timings_ms"]["openapi_docs"] = round((time.perf_counter() - t0) * 1000, 1)

            # health
            t0 = time.perf_counter()
            h = client.get("/api/health")
            results["timings_ms"]["health"] = round((time.perf_counter() - t0) * 1000, 1)
            assert h.status_code == 200 and h.json()["database"] == "ok"
            results["steps"]["health"] = h.json()
            print("[1] health:", h.json()["status"], "| model:", h.json()["model"]["state"],
                  f"({results['timings_ms']['health']} ms)")

            # upload (real parser)
            t0 = time.perf_counter()
            up = client.post("/api/contracts/upload",
                             files={"upload": ("tiny consulting.txt",
                                               TINY_CONTRACT.encode("utf-8"), "text/plain")})
            results["timings_ms"]["upload"] = round((time.perf_counter() - t0) * 1000, 1)
            assert up.status_code == 201, up.text
            cid = up.json()["id"]
            results["steps"]["upload"] = up.json()
            print(f"[2] upload: {cid[:8]}... {up.json()['file_type']} "
                  f"{up.json()['character_count']} chars ({results['timings_ms']['upload']} ms)")

            # analyze with the REAL fine-tuned model
            t0 = time.perf_counter()
            ra = client.post(f"/api/contracts/{cid}/analyze")
            results["timings_ms"]["analyze"] = round((time.perf_counter() - t0) * 1000, 1)
            assert ra.status_code == 200, ra.text
            print(f"[3] analyze: {ra.json()} ({results['timings_ms']['analyze']} ms incl. model load)")

            # analysis retrieval
            t0 = time.perf_counter()
            full = client.get(f"/api/contracts/{cid}/analysis").json()
            results["timings_ms"]["analysis_fetch"] = round((time.perf_counter() - t0) * 1000, 1)
            found = [c for c in full["clauses"] if c["found"]]
            results["steps"]["analysis"] = {
                "status": full["status"],
                "overall_risk": full["overall_risk"],
                "found_clauses": {c["clause_type"]: round(c["confidence"], 3) for c in found},
                "entities": {k: v for k, v in full["entities"].__dict__.items() if v} if hasattr(full["entities"], "__dict__") else full["entities"],
                "risk_findings": [f["rule_id"] for f in full["risk_findings"]],
            }
            print(f"[4] analysis: risk {full['overall_risk']['score']} "
                  f"({full['overall_risk']['level']}) | found: "
                  f"{results['steps']['analysis']['found_clauses']}")
            print(f"    entities: {results['steps']['analysis']['entities']}")
            print(f"    rules: {results['steps']['analysis']['risk_findings']}")
            # evidence substring property
            text = client.get(f"/api/contracts/{cid}/text").json()["text"]
            for c in found:
                assert text[c["start_char"]:c["end_char"]] == c["text"]
            results["steps"]["evidence_substring_check"] = True

            # stats + list
            t0 = time.perf_counter()
            st = client.get("/api/stats").json()
            lst = client.get("/api/contracts").json()
            results["timings_ms"]["stats_and_list"] = round((time.perf_counter() - t0) * 1000, 1)
            results["steps"]["stats"] = st
            print(f"[5] stats: {st} | list total={lst['total']} "
                  f"({results['timings_ms']['stats_and_list']} ms)")

            # delete
            assert client.delete(f"/api/contracts/{cid}").status_code == 200
            assert client.get(f"/api/contracts/{cid}").status_code == 404
            results["steps"]["delete"] = "ok"
            print("[6] delete: ok")

    out = PROJECT_ROOT / "reports" / "phase5_smoke_api.json"
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nAPI SMOKE TEST PASSED -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
