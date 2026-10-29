"""Final synthesis — uses Nemotron-3-Ultra to generate the human-readable report.

This is the most expensive tier ($1.00/1M input) and is called ONCE per document
at the very end, after all deterministic verification is complete.

The synthesizer receives the already-verified claims and simply produces
a readable summary. It does NOT make verification decisions.
"""

import logging

from models.claim import Claim, ClaimStatus
from .model_router import call_model

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """\
You are a document verification report writer. You will receive a list of claims
that have ALREADY been verified by a deterministic evidence system.

Your job is to write a clear, concise summary of the verification findings.
Do NOT change any verification status — those decisions are final.

Write a 2-3 paragraph summary that covers:
1. What the document is about
2. Key findings (most important verified and contradicted claims)
3. Overall assessment and recommended next steps

Keep it professional, factual, and actionable. No hedging or filler.
"""


async def generate_summary(
    document_name: str,
    claims: list[Claim],
    document_type: str,
) -> str:
    """Generate a human-readable summary using Nemotron-3-Ultra.

    This is called once, at the end of the pipeline, after all verification
    is complete. The Ultra model summarizes but does NOT verify.

    Args:
        document_name: Name of the uploaded document.
        claims: All claims with their final verification status.
        document_type: Detected document type.

    Returns:
        Human-readable summary string.
    """
    verified = [c for c in claims if c.status == ClaimStatus.VERIFIED]
    contradicted = [c for c in claims if c.status == ClaimStatus.CONTRADICTED]
    unverifiable = [c for c in claims if c.status == ClaimStatus.UNVERIFIABLE]

    claims_summary = (
        f"Document: {document_name}\n"
        f"Type: {document_type}\n"
        f"Total claims: {len(claims)}\n"
        f"Verified: {len(verified)}\n"
        f"Contradicted: {len(contradicted)}\n"
        f"Unverifiable: {len(unverifiable)}\n\n"
    )

    if contradicted:
        claims_summary += "CONTRADICTED CLAIMS:\n"
        for c in contradicted[:5]:
            claims_summary += f"  - {c.text} (Reason: {c.verification_reason})\n"
        claims_summary += "\n"

    if verified:
        claims_summary += "KEY VERIFIED CLAIMS:\n"
        for c in verified[:5]:
            claims_summary += f"  - {c.text}\n"
        claims_summary += "\n"

    if unverifiable:
        claims_summary += "UNVERIFIABLE CLAIMS:\n"
        for c in unverifiable[:3]:
            claims_summary += f"  - {c.text}\n"

    try:
        summary = await call_model(
            task_type="final_synthesis",
            system_prompt=SYNTHESIS_PROMPT,
            user_prompt=claims_summary,
            temperature=0.3,
            max_tokens=1024,
        )
        return summary.strip()
    except Exception:
        logger.exception("Summary generation failed — falling back to template")
        return _fallback_summary(document_name, len(claims), len(verified), len(contradicted))


def _fallback_summary(name: str, total: int, verified: int, contradicted: int) -> str:
    """Template-based fallback if Ultra model call fails."""
    return (
        f"Verification of '{name}' analyzed {total} claims. "
        f"{verified} claims were verified against live evidence, "
        f"and {contradicted} claims were contradicted. "
        f"Review the detailed evidence chain for each flagged claim."
    )
