"""Regression test: run every challenge document through a live backend and assert the outcome.

Usage (backend running on :8000):  python eval_challenges.py [base_url]
Exits non-zero if any check fails.
"""

import sys
import time

import httpx

from routers.challenge import CHALLENGES

# Findings quote look-alike characters (e.g. Cyrillic letters). Windows consoles and redirected
# output default to cp1252, which cannot encode them, so force UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = _args[0] if _args else "http://localhost:8000"
WITH_BASELINE = "--baseline" in sys.argv  # also ask a plain Ultra review (informational, no assertions)
HIGH = {"high", "critical"}

CONTROL = (
    "The Eiffel Tower is located in Paris, France. It was completed in 1889 "
    "for the World's Fair. It is about 330 metres tall."
)


def kinds(report):
    return {f["kind"] for f in report["findings"]}


def claim_has(report, word, verdict=None):
    for cv in report["claim_verifications"]:
        if word.lower() in cv["claim"]["text"].lower() and (verdict is None or cv["verdict"] == verdict):
            return True
    return False


CHECKS = {
    "homograph-attack": [
        ("HOMOGRAPH_DOMAIN finding", lambda r: "HOMOGRAPH_DOMAIN" in kinds(r)),
        ("risk is high or critical", lambda r: r["risk_level"] in HIGH),
    ],
    "prompt-injection": [
        ("PROMPT_INJECTION finding", lambda r: "PROMPT_INJECTION" in kinds(r)),
        ("INVALID_DATE finding", lambda r: "INVALID_DATE" in kinds(r)),
        ("February 30 claim not verified", lambda r: not claim_has(r, "february 30", "verified")),
        ("risk is high or critical", lambda r: r["risk_level"] in HIGH),
    ],
    "fabricated-entity": [
        ("no USBAIS/Bureau claim verified",
         lambda r: not (claim_has(r, "usbais", "verified") or claim_has(r, "bureau", "verified"))),
        ("risk is not low", lambda r: r["risk_level"] != "low"),
    ],
    "contradictory-terms": [
        ("at least 2 contradicted claims", lambda r: r["contradicted_count"] >= 2),
        ("risk is high or critical", lambda r: r["risk_level"] in HIGH),
    ],
    "invoice-fraud": [
        ("HOMOGRAPH_DOMAIN finding", lambda r: "HOMOGRAPH_DOMAIN" in kinds(r)),
        ("risk is high or critical", lambda r: r["risk_level"] in HIGH),
    ],
    "control": [
        ("no contradicted claims", lambda r: r["contradicted_count"] == 0),
        ("no findings", lambda r: not r["findings"]),
        ("risk is low or medium", lambda r: r["risk_level"] in ("low", "medium")),
    ],
}


def run(client, name, text):
    t0 = time.time()
    resp = client.post("/api/verify", files={"file": (f"{name}.txt", text.encode("utf-8"), "text/plain")})
    resp.raise_for_status()
    return resp.json(), time.time() - t0


def main() -> int:
    docs = [(c["id"], c["document_text"]) for c in CHALLENGES] + [("control", CONTROL)]
    failures = 0
    with httpx.Client(base_url=BASE, timeout=180.0) as client:
        for cid, text in docs:
            try:
                report, secs = run(client, cid, text)
            except Exception as exc:
                print(f"[ERROR] {cid}: {type(exc).__name__}: {exc}")
                failures += 1
                continue
            print(f"\n== {cid}  trust={report['trust_score']} risk={report['risk_level']} "
                  f"V/U/C={report['verified_count']}/{report['unverifiable_count']}/{report['contradicted_count']} "
                  f"{secs:.0f}s tokens={report['model_tier_usage']}")
            for f in report["findings"]:
                print(f"   finding {f['kind']}: {f['quote'][:70]}")
            for n in report["analysis_notes"]:
                print(f"   note: {n}")
            for check, fn in CHECKS[cid]:
                ok = bool(fn(report))
                failures += 0 if ok else 1
                print(f"   [{'PASS' if ok else 'FAIL'}] {check}")
            if WITH_BASELINE:
                try:
                    resp = client.post(
                        "/api/baseline", files={"file": (f"{cid}.txt", text.encode("utf-8"), "text/plain")}
                    )
                    resp.raise_for_status()
                    b = resp.json()
                    print(f"   plain LLM: {b['verdict']} ({b['confidence']}%) - {b['reasoning'][:160]}")
                except Exception as exc:
                    print(f"   plain LLM: error {type(exc).__name__}: {exc}")
    print(f"\n{'ALL PASSED' if failures == 0 else str(failures) + ' CHECK(S) FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
