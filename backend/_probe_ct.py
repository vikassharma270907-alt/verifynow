"""Temporary probe: run the contradictory-terms challenge twice. Delete after use."""
import sys

import httpx

from routers.challenge import CHALLENGES

doc = next(c for c in CHALLENGES if c["id"] == "contradictory-terms")["document_text"]
port = sys.argv[1] if len(sys.argv) > 1 else "8000"
with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=240) as c:
    for i in range(3):
        r = c.post("/api/verify", files={"file": ("ct.txt", doc.encode(), "text/plain")}).json()
        print(f"run {i + 1}: risk={r['risk_level']} V/U/C={r['verified_count']}/{r['unverifiable_count']}/"
              f"{r['contradicted_count']} {r['processing_time_ms']}ms", flush=True)
        for f in r["findings"]:
            print("   finding", f["kind"], f["quote"][:90], flush=True)
        for n in r["analysis_notes"]:
            print("   note:", n, flush=True)
        for cv in r["claim_verifications"]:
            print("   ", cv["verdict"], "|", cv["claim"]["text"][:80], flush=True)
