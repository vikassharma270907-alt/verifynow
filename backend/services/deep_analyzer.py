"""Deep analysis — uses Nemotron-3-Super for contradiction detection and reasoning.

This runs on the mid-tier model ($0.30/1M input, 127 Tok/s) and is only invoked
for claims that need deeper reasoning — not for every claim.

Routing rule: Only claims with category "legal", "financial", or "regulatory"
and confidence < 0.9 get escalated to deep analysis.
"""

import json
import logging

from models.claim import Claim
from models.evidence import Evidence, EvidenceSource
from .model_router import call_model

logger = logging.getLogger(__name__)

DEEP_ANALYSIS_PROMPT = """\
You are a document verification specialist. Analyze the following claim extracted
from a document, along with the evidence found via web search.

Your job is to determine whether the evidence SUPPORTS or CONTRADICTS the claim.
Be precise and cite specific reasons.

Return ONLY valid JSON:
{
  "supports_claim": true or false,
  "reasoning": "Specific explanation of why the evidence supports or contradicts",
  "contradiction_details": "If contradicted, explain the specific discrepancy",
  "confidence": 0.0 to 1.0
}
"""

# Only escalate these categories to deep analysis
ESCALATION_CATEGORIES = {"legal", "financial", "regulatory"}
ESCALATION_CONFIDENCE_THRESHOLD = 0.9


def should_escalate(claim: Claim) -> bool:
    """Determine if a claim needs deep analysis (Super tier) or can stay on Nano."""
    return (
        claim.category in ESCALATION_CATEGORIES
        and claim.confidence < ESCALATION_CONFIDENCE_THRESHOLD
    )


async def analyze_claim_evidence(
    claim: Claim,
    evidence: list[Evidence],
) -> list[Evidence]:
    """Use Nemotron-3-Super to assess whether evidence supports or contradicts a claim.

    This enriches the Evidence objects with accurate supports_claim values
    based on deeper reasoning.

    Args:
        claim: The claim being analyzed.
        evidence: Raw evidence from Tavily search.

    Returns:
        Updated evidence list with refined supports_claim flags.
    """
    if not evidence:
        return evidence

    # Build context from evidence
    evidence_texts = []
    for i, ev in enumerate(evidence):
        evidence_texts.append(
            f"[Source {i+1}] {ev.source_title or 'Unknown'}\n"
            f"URL: {ev.source_url or 'N/A'}\n"
            f"Content: {ev.content[:500]}"
        )

    user_prompt = (
        f"CLAIM: {claim.text}\n"
        f"CATEGORY: {claim.category}\n"
        f"ENTITIES: {', '.join(claim.entities)}\n\n"
        f"EVIDENCE:\n" + "\n\n".join(evidence_texts)
    )

    try:
        raw = await call_model(
            task_type="contradiction_detection",
            system_prompt=DEEP_ANALYSIS_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        logger.exception("Deep analysis failed for claim: %s", claim.text[:80])
        return evidence

    supports = data.get("supports_claim", True)
    reasoning = data.get("reasoning", "")

    # Update all evidence items with the deep analysis result
    for ev in evidence:
        ev.supports_claim = supports

    # If contradicted, add the reasoning as a new evidence item
    if not supports and reasoning:
        contradiction_evidence = Evidence(
            source_type=EvidenceSource.DETERMINISTIC_CHECK,
            content=f"Deep analysis: {reasoning}",
            supports_claim=False,
            relevance_score=data.get("confidence", 0.8),
            retrieved_at=evidence[0].retrieved_at if evidence else "",
        )
        evidence.append(contradiction_evidence)

    return evidence
