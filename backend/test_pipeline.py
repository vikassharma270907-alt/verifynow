"""Quick end-to-end test of the VerifyFlow pipeline."""

import httpx

TEST_DOC = """SERVICE AGREEMENT

Section 3.1: The service period begins on January 1, 2027 and terminates on December 31, 2027 (12-month term).

Section 3.2: The initial term of this agreement is 24 months, commencing on the Effective Date defined in Section 3.1.

Section 7.1: Either party may terminate with 30 days written notice.

Section 7.4: This agreement cannot be terminated before the end of the initial term under any circumstances.
"""


def main():
    print("Sending document to VerifyFlow pipeline...")
    resp = httpx.post(
        "http://localhost:8000/api/verify",
        files={"file": ("test-contract.txt", TEST_DOC.encode(), "text/plain")},
        timeout=120.0,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} — {resp.text[:500]}")
        return

    data = resp.json()

    print("\n=== TRUST SCORECARD ===")
    print(f"Document:    {data['document_name']}")
    print(f"Type:        {data['document_type']}")
    print(f"Trust Score: {data['trust_score']}%")
    print(f"Risk Level:  {data['risk_level']}")
    print(f"Claims:      {data['total_claims']} total")
    print(f"  Verified:      {data['verified_count']}")
    print(f"  Unverifiable:  {data['unverifiable_count']}")
    print(f"  Contradicted:  {data['contradicted_count']}")
    print(f"Time:        {data['processing_time_ms']}ms")
    usage = data.get("model_tier_usage", {})
    print(f"Tokens:      Nano={usage.get('nano',0)} Super={usage.get('super',0)} Ultra={usage.get('ultra',0)}")

    print("\n=== SUMMARY ===")
    print(data["summary"])

    print("\n=== CLAIMS ===")
    icons = {"verified": "✅", "contradicted": "❌", "unverifiable": "⚠️"}
    for cv in data["claim_verifications"]:
        icon = icons.get(cv["verdict"], "❓")
        print(f"{icon} {cv['claim']['text']}")
        print(f"   Reason: {cv['claim']['verification_reason']}")
        print(f"   Evidence: {len(cv['evidence'])} sources")
        print()


if __name__ == "__main__":
    main()
