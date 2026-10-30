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
from services.claim_checks import agreement
from services.logsafe import safe_http_url

logger = logging.getLogger(__name__)

# Note: relevance_score is deliberately NOT capped for evidence that does not textually
# agree with the claim. The verifier's stance/quote gate plus the Super judge decide, and
# capping would hide judged evidence. Neutral results are flagged supports_claim=False.


def _to_str(value: object) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def _to_score(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        score = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if score != score:  # NaN
        return 0.0
    return min(max(score, 0.0), 1.0)


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
        "query": query,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "search_depth": "advanced",
    }
    # Key travels in the Authorization header (from env config), never in the body.
    headers = {"Authorization": "Bearer " + TAVILY_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(TAVILY_SEARCH_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Tavily search failed (status %s)", exc.response.status_code)
        return []
    except Exception as exc:
        # Log only the exception type: messages/tracebacks could echo request headers.
        logger.error("Tavily search request failed (%s)", type(exc).__name__)
        return []

    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        return []

    now = datetime.now(timezone.utc).isoformat()
    evidence_list: list[Evidence] = []

    for result in data["results"]:
        if not isinstance(result, dict):
            continue
        content = _to_str(result.get("content"))[:1000]  # Cap content length
        # Support is decided deterministically, never assumed. Stance stays
        # "unjudged" so the judge + verifier gate still make the final call.
        supports = agreement(claim_text, content) == "supports"
        evidence = Evidence(
            source_type=EvidenceSource.TAVILY_SEARCH,
            # Only http(s) URLs reach the UI; javascript:/data: links are dropped.
            source_url=safe_http_url(result.get("url")),
            source_title=_to_str(result.get("title")),
            content=content,
            supports_claim=supports,
            relevance_score=_to_score(result.get("score")),
            retrieved_at=now,
        )
        evidence_list.append(evidence)

    logger.info("Found %d Tavily results for claim: %s", len(evidence_list), claim_text[:80])
    return evidence_list
