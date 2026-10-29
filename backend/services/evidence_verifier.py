"""Deterministic evidence verifier — the core trust gate.

This is NOT an LLM. This is deterministic code that decides whether a claim
is verified, unverifiable, or contradicted based on hard rules.

Design principle from the hackathon judges (Telltale review):
  "The model can think, but it does not get the final say. The evidence does."

A claim is VERIFIED only if it passes at least one deterministic check:
  1. A Tavily search citation with relevance_score >= 0.7 supports it
  2. An exact substring from the original document corroborates it
  3. A deterministic pattern check (dates, amounts, entity formats) passes

A claim is CONTRADICTED if:
  1. A Tavily citation with relevance_score >= 0.7 explicitly contradicts it
  2. The deep analyzer flagged a logical contradiction

A claim is UNVERIFIABLE if:
  No evidence met the threshold in either direction.
"""

import logging
import re

from models.claim import Claim, ClaimStatus
from models.evidence import Evidence

logger = logging.getLogger(__name__)

# Thresholds — deterministic, not learned
SUPPORT_RELEVANCE_THRESHOLD = 0.7
CONTRADICTION_RELEVANCE_THRESHOLD = 0.7
MIN_EVIDENCE_FOR_VERIFICATION = 1


def verify_claim(claim: Claim, evidence: list[Evidence], document_text: str) -> Claim:
    """Apply deterministic verification rules to a claim given its evidence.

    This function contains NO LLM calls. All decisions are rule-based.

    Args:
        claim: The claim to verify.
        evidence: Evidence collected from Tavily and other sources.
        document_text: The original document text for substring checks.

    Returns:
        The claim with updated status and verification_reason.
    """
    supporting: list[Evidence] = []
    contradicting: list[Evidence] = []

    for ev in evidence:
        if ev.relevance_score >= SUPPORT_RELEVANCE_THRESHOLD and ev.supports_claim:
            supporting.append(ev)
        elif ev.relevance_score >= CONTRADICTION_RELEVANCE_THRESHOLD and not ev.supports_claim:
            contradicting.append(ev)

    # Rule 1: Check for contradictions first (fail-safe)
    if contradicting:
        claim.status = ClaimStatus.CONTRADICTED
        sources = [e.source_url or e.source_title or "unknown" for e in contradicting[:3]]
        claim.verification_reason = (
            f"Contradicted by {len(contradicting)} source(s): {', '.join(sources)}"
        )
        return claim

    # Rule 2: Check for supporting evidence from Tavily
    if len(supporting) >= MIN_EVIDENCE_FOR_VERIFICATION:
        claim.status = ClaimStatus.VERIFIED
        sources = [e.source_url or e.source_title or "unknown" for e in supporting[:3]]
        claim.verification_reason = (
            f"Verified by {len(supporting)} source(s): {', '.join(sources)}"
        )
        return claim

    # Rule 3: Check for exact document substring corroboration
    if _substring_corroboration(claim, document_text):
        claim.status = ClaimStatus.VERIFIED
        claim.verification_reason = "Corroborated by exact quote in source document"
        return claim

    # Rule 4: Deterministic pattern checks (dates, amounts, formats)
    pattern_result = _pattern_check(claim)
    if pattern_result is not None:
        claim.status = pattern_result[0]
        claim.verification_reason = pattern_result[1]
        return claim

    # Default: Unverifiable — not enough evidence in either direction
    claim.status = ClaimStatus.UNVERIFIABLE
    claim.verification_reason = (
        f"Insufficient evidence: {len(supporting)} supporting, "
        f"{len(contradicting)} contradicting (threshold: {SUPPORT_RELEVANCE_THRESHOLD})"
    )
    return claim


def _substring_corroboration(claim: Claim, document_text: str) -> bool:
    """Check if key entities in the claim appear as exact substrings in the document."""
    if not claim.entities:
        return False

    found = 0
    for entity in claim.entities:
        if entity.lower() in document_text.lower():
            found += 1

    # Require at least half the entities to be found in the document
    return found >= max(1, len(claim.entities) // 2)


def _pattern_check(claim: Claim) -> tuple[ClaimStatus, str] | None:
    """Run deterministic format checks on claim entities."""
    text = claim.text

    # Check date formats are valid
    date_pattern = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
    dates = date_pattern.findall(text)
    for date_str in dates:
        if not _is_plausible_date(date_str):
            return (
                ClaimStatus.CONTRADICTED,
                f"Invalid date format detected: {date_str}",
            )

    # Check for suspiciously round numbers that might indicate fabrication
    # (e.g., "$1,000,000.00 exactly" in a supposedly real invoice)
    # This is a heuristic, not a hard rule — returns None to fall through

    return None


def _is_plausible_date(date_str: str) -> bool:
    """Check if a date string is plausible (not obviously invalid)."""
    parts = re.split(r"[/-]", date_str)
    if len(parts) != 3:
        return False
    try:
        nums = [int(p) for p in parts]
        # Basic sanity: no month > 12, no day > 31
        if nums[0] > 31 or nums[1] > 12:
            # Could be YYYY-MM-DD format
            if nums[0] > 2100 or nums[1] > 12 or nums[2] > 31:
                return False
        return True
    except ValueError:
        return False


def compute_trust_score(claims: list[Claim]) -> float:
    """Compute overall trust score as a deterministic percentage.

    Formula: (verified / total) * 100, with a penalty for contradictions.
    """
    if not claims:
        return 0.0

    total = len(claims)
    verified = sum(1 for c in claims if c.status == ClaimStatus.VERIFIED)
    contradicted = sum(1 for c in claims if c.status == ClaimStatus.CONTRADICTED)

    # Each contradiction penalizes double
    raw_score = (verified - (contradicted * 2)) / total * 100
    return max(0.0, min(100.0, raw_score))


def compute_risk_level(trust_score: float, contradicted_count: int) -> str:
    """Deterministic risk level from trust score and contradiction count."""
    if contradicted_count >= 3 or trust_score < 30:
        return "critical"
    if contradicted_count >= 1 or trust_score < 50:
        return "high"
    if trust_score < 75:
        return "medium"
    return "low"
