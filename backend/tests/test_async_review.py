"""Regression tests from the python-reviewer pass (task 5.3)."""

import asyncio

import pytest

from models.claim import Claim, ClaimStatus
from routers import verify


def _claim(i: int) -> Claim:
    return Claim(
        id=f"claim-{i}", text=f"Claim number {i}", category="factual",
        source_location="x", confidence=0.9, status=ClaimStatus.PENDING, entities=[],
    )


@pytest.mark.asyncio
async def test_gather_evidence_cancels_and_awaits_stragglers(monkeypatch):
    """Tasks past the deadline are reported unchecked and fully finished (not left pending)."""
    started: list[asyncio.Task] = []

    async def slow_search(claim_text, entities=None, max_results=3):
        started.append(asyncio.current_task())
        await asyncio.sleep(30)
        return []

    monkeypatch.setattr(verify, "search_evidence_for_claim", slow_search)
    claims = [_claim(i) for i in range(6)]  # more than SEARCH_CONCURRENCY
    evidence, unchecked = await verify._gather_evidence(claims, timeout=0.05)

    assert evidence == {}
    assert unchecked == {c.id for c in claims}
    assert all(t.done() for t in started)
    leftovers = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    assert all(t.done() for t in leftovers)
