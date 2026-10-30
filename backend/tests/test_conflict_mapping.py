"""Deterministic conflict validation: quotes are checked against the document and mapped to claims.

No network. The model's proposals are given as plain dicts.
"""

from models.claim import Claim, ClaimStatus
from services.evidence_verifier import conflict_reasons, validate_conflicts

DOC = (
    "Section 3.1: The service period begins on January 1, 2027 and terminates on "
    "December 31, 2027 (12-month term).\n"
    "Section 3.2: The initial term of this agreement is 24 months, commencing on the "
    "Effective Date defined in Section 3.1.\n"
    "Section 7.1: Either party may terminate with 30 days written notice.\n"
    "Section 7.4: This agreement cannot be terminated before the end of the initial term "
    "under any circumstances."
)


def claim(cid: str, text: str) -> Claim:
    return Claim(
        id=cid, text=text, category="legal", source_location="s", confidence=0.9,
        status=ClaimStatus.PENDING, entities=[],
    )


CLAIMS = [
    claim("c1", "The service period begins on January 1, 2027 and terminates on December 31, 2027"),
    claim("c2", "The initial term of this agreement is 24 months"),
    claim("c3", "Either party may terminate with 30 days written notice"),
    claim("c4", "This agreement cannot be terminated before the end of the initial term"),
]

TERM_CONFLICT = {
    "quote_a": "The service period begins on January 1, 2027 and terminates on December 31, 2027 (12-month term).",
    "quote_b": "The initial term of this agreement is 24 months",
    "reason": "12 months vs 24 months",
}


def test_quotes_are_mapped_to_the_claims_they_state():
    conflicts = validate_conflicts([TERM_CONFLICT], CLAIMS, DOC)
    assert len(conflicts) == 1
    assert {conflicts[0].claim_a, conflicts[0].claim_b} == {"c1", "c2"}
    reasons = conflict_reasons(conflicts)
    assert set(reasons) == {"c1", "c2"}


def test_model_supplied_claim_ids_are_ignored():
    proposal = dict(TERM_CONFLICT, claim_a="c3", claim_b="c4")  # wrong ids from the model
    conflicts = validate_conflicts([proposal], CLAIMS, DOC)
    assert {conflicts[0].claim_a, conflicts[0].claim_b} == {"c1", "c2"}


def test_non_verbatim_quote_is_rejected():
    proposal = dict(TERM_CONFLICT, quote_b="The initial term of this agreement is 36 months")
    assert validate_conflicts([proposal], CLAIMS, DOC) == []


def test_conflict_without_matching_claim_is_kept_as_document_finding():
    conflicts = validate_conflicts([TERM_CONFLICT], [claim("x", "Rent is due monthly")], DOC)
    assert len(conflicts) == 1
    assert conflicts[0].claim_a is None and conflicts[0].claim_b is None
    assert conflict_reasons(conflicts) == {}


def test_duplicate_proposals_are_counted_once():
    assert len(validate_conflicts([TERM_CONFLICT, dict(TERM_CONFLICT)], CLAIMS, DOC)) == 1


def test_both_sides_never_map_to_the_same_claim():
    conflicts = validate_conflicts([TERM_CONFLICT], [CLAIMS[0]], DOC)
    assert conflicts[0].claim_a == "c1"
    assert conflicts[0].claim_b is None
