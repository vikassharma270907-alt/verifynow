"""Claim extraction — uses Nemotron-3-Nano to pull structured claims from documents.

This is the first pipeline stage. It runs on the cheapest tier ($0.06/1M input)
because claim extraction is high-volume but doesn't need deep reasoning.
"""

import json
import logging
import uuid

from models.claim import Claim, ClaimStatus
from .model_router import call_model

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """\
You are a document analysis specialist. Extract all verifiable factual claims from the
provided document text. For each claim, identify:

1. The exact claim text
2. The category (legal, financial, identity, temporal, regulatory, factual)
3. Where it appears in the document (paragraph number or section)
4. Your confidence in the extraction (0.0 to 1.0)
5. Named entities mentioned (people, organizations, dates, amounts, addresses)

Return ONLY valid JSON in this format:
{
  "claims": [
    {
      "text": "The lease term begins on January 1, 2027",
      "category": "temporal",
      "source_location": "Section 2, paragraph 1",
      "confidence": 0.95,
      "entities": ["January 1, 2027"]
    }
  ]
}

Focus on claims that can be externally verified — dates, amounts, entity names,
regulatory references, legal citations, and factual assertions.
Do NOT extract opinions, subjective statements, or boilerplate language.
"""


async def extract_claims(document_text: str) -> list[Claim]:
    """Extract verifiable claims from document text using Nemotron-3-Nano.

    Args:
        document_text: The full text content of the document.

    Returns:
        List of Claim objects with PENDING status.
    """
    if not document_text.strip():
        return []

    # Truncate very long documents to stay within context window
    max_chars = 500_000  # ~125K tokens for Nano's 1M context
    if len(document_text) > max_chars:
        document_text = document_text[:max_chars]
        logger.warning("Document truncated to %d chars for claim extraction", max_chars)

    raw = await call_model(
        task_type="claim_extraction",
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
        user_prompt=f"Extract all verifiable claims from this document:\n\n{document_text}",
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse claim extraction JSON: %s", raw[:500])
        return []

    claims: list[Claim] = []
    for item in data.get("claims", []):
        claim = Claim(
            id=f"claim-{uuid.uuid4().hex[:8]}",
            text=item.get("text", ""),
            category=item.get("category", "factual"),
            source_location=item.get("source_location", "unknown"),
            confidence=min(max(float(item.get("confidence", 0.5)), 0.0), 1.0),
            status=ClaimStatus.PENDING,
            entities=item.get("entities", []),
        )
        if claim.text.strip():
            claims.append(claim)

    logger.info("Extracted %d claims from document", len(claims))
    return claims
