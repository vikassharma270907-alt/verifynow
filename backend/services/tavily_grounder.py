"""Tavily live search grounding — verifies claims against real-time web evidence.

This is the second pipeline stage. For each extracted claim, we query Tavily's
search API to find supporting or contradicting evidence from the live web.
Results are returned as structured Evidence objects with source URLs for citations.
"""

import logging
from datetime import datetime, timezone

import httpx

from config import TAVILY_API_KEY, TAVILY_SEARCH_URL
from models.evidence import Evidence, EvidenceSource

logger = logging.getLogger(__name__)


async def search_evidence_for_claim(
    claim_text: str,
    entities: list[str] | None = None,
    max_results: int = 5,
) -> list[Evidence]:
    """Query Tavily to find live web evidence for a specific claim.

    Args:
        claim_text: The claim to verify.
        entities: Named entities to include in the search query.
        max_results: Maximum number of search results.

    Returns:
        List of Evidence objects from Tavily search.
    """
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set — skipping live search grounding")
        return []

    # Build a focused search query from the claim and its entities
    query = claim_text[:400]  # Tavily query length limit
    if entities:
        entity_str = " ".join(entities[:3])
        query = f"{entity_str} {query}"[:400]

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "search_depth": "advanced",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(TAVILY_SEARCH_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Tavily search failed (%s): %s", exc.response.status_code, exc.response.text[:300])
        return []
    except Exception:
        logger.exception("Tavily search request failed for claim: %s", claim_text[:100])
        return []

    now = datetime.now(timezone.utc).isoformat()
    evidence_list: list[Evidence] = []

    for result in data.get("results", []):
        evidence = Evidence(
            source_type=EvidenceSource.TAVILY_SEARCH,
            source_url=result.get("url", ""),
            source_title=result.get("title", ""),
            content=result.get("content", "")[:1000],  # Cap content length
            supports_claim=True,  # Will be refined by evidence_verifier
            relevance_score=min(max(result.get("score", 0.5), 0.0), 1.0),
            retrieved_at=now,
        )
        evidence_list.append(evidence)

    logger.info("Found %d Tavily results for claim: %s", len(evidence_list), claim_text[:80])
    return evidence_list
