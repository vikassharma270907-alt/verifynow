"""Main verification endpoint.

Flow:
  1. Validate upload and extract text
  2. Deterministic checks on the raw text (dates, look-alike domains, injection)
  3. Nano extracts claims
  4. Tavily searches evidence for every claim (parallel)
  5. Super PROPOSES stances and internal conflicts (one batched call each)
  6. Deterministic verifier decides every verdict (no model calls)
  7. Ultra writes the summary
"""

import asyncio
import io
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB
from models.claim import Claim, ClaimStatus
from models.evidence import Evidence
from models.finding import DocumentFinding, FindingKind, Severity
from models.report import ClaimVerification, VerificationReport
from services.claim_extractor import extract_claims
from services.deep_analyzer import judge_evidence, propose_conflicts
from services.document_checks import run_document_checks
from services.errors import UpstreamError
from services.evidence_verifier import (
    compute_risk_level,
    compute_trust_score,
    conflict_reasons,
    unrecognized_authority,
    validate_conflicts,
    verify_claim,
)
from services.model_router import get_usage, start_request_usage
from services.synthesizer import generate_summary
from services.tavily_grounder import search_evidence_for_claim

logger = logging.getLogger(__name__)
router = APIRouter(tags=["verification"])

MAX_CLAIMS = 20
SEARCH_CONCURRENCY = 4

# Public demos spend real API credits. Limit each client to N verifications per hour
# (RATE_LIMIT_PER_HOUR, 0 disables). In-memory, so it resets on restart.
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "30"))
_hits: dict[str, deque] = defaultdict(deque)


def _enforce_rate_limit(request: Request) -> None:
    if RATE_LIMIT_PER_HOUR <= 0:
        return
    forwarded = request.headers.get("x-forwarded-for", "")
    client = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    now = time.time()
    window = _hits[client]
    while window and now - window[0] > 3600:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached ({RATE_LIMIT_PER_HOUR} verifications per hour). Try again later.",
        )
    window.append(now)
    if len(_hits) > 5000:  # keep memory bounded
        for key in [k for k, v in _hits.items() if not v or now - v[-1] > 3600]:
            del _hits[key]


def _extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            logger.exception("PDF parsing failed")
            raise HTTPException(status_code=422, detail="Failed to parse PDF file")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


async def _gather_evidence(claims: list[Claim]) -> dict[str, list[Evidence]]:
    sem = asyncio.Semaphore(SEARCH_CONCURRENCY)

    async def one(claim: Claim) -> list[Evidence]:
        async with sem:
            return await search_evidence_for_claim(
                claim_text=claim.text, entities=claim.entities, max_results=3
            )

    results = await asyncio.gather(*(one(c) for c in claims))
    return {c.id: evs for c, evs in zip(claims, results)}


def _detect_document_type(text: str) -> str:
    lower = text.lower()
    if any(kw in lower for kw in ["lease", "tenant", "landlord", "rent"]):
        return "lease_agreement"
    if any(kw in lower for kw in ["invoice", "amount due", "bill to"]):
        return "invoice"
    if any(kw in lower for kw in ["contract", "agreement", "parties", "hereby"]):
        return "contract"
    if any(kw in lower for kw in ["terms of service", "privacy policy", "user agreement"]):
        return "terms_of_service"
    if any(kw in lower for kw in ["resume", "curriculum vitae"]):
        return "resume"
    return "general_document"


async def _no_conflicts() -> tuple[list[dict], None]:
    return [], None


@router.post("/api/verify", response_model=VerificationReport)
async def verify_document(request: Request, file: UploadFile = File(...)):
    _enforce_rate_limit(request)
    start = time.time()
    start_request_usage()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    name = Path(file.filename).name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE_MB}MB")

    text = _extract_text(name, content)
    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the document")

    notes: list[str] = []
    findings: list[DocumentFinding] = run_document_checks(text)

    try:
        claims = (await extract_claims(text))[:MAX_CLAIMS]
    except UpstreamError as exc:
        logger.error("Claim extraction upstream error: status=%s", exc.status)
        raise HTTPException(status_code=exc.status, detail=exc.safe_message)
    except Exception as exc:
        logger.exception("Claim extraction failed")
        raise HTTPException(status_code=502, detail=f"Claim extraction failed: {type(exc).__name__}")

    if not claims:
        notes.append("No verifiable claims were extracted from this document.")

    evidence_map = await _gather_evidence(claims) if claims else {}
    if claims and not any(evidence_map.values()):
        notes.append("Web search returned no results (missing key or search failure). Claims are unverified.")

    proposals: list[dict] = []
    if claims:
        judge_note, (proposals, conflict_note) = await asyncio.gather(
            judge_evidence(claims, evidence_map),
            propose_conflicts(claims, text) if len(claims) >= 2 else _no_conflicts(),
        )
        notes.extend(n for n in (judge_note, conflict_note) if n)

    conflicts = validate_conflicts(proposals, claims, text)
    reasons = conflict_reasons(conflicts)
    for c in conflicts:
        findings.append(
            DocumentFinding(
                kind=FindingKind.INTERNAL_CONFLICT,
                severity=Severity.HIGH,
                quote=f'"{c.quote_a}" vs "{c.quote_b}"',
                explanation=c.reason,
                claim_id=c.claim_a,
            )
        )

    # Attach impossible-date findings to the claim that contains the date.
    date_for_claim: dict[str, DocumentFinding] = {}
    for f in findings:
        if f.kind == FindingKind.INVALID_DATE and f.claim_id is None:
            for claim in claims:
                if f.quote.lower() in claim.text.lower() and claim.id not in date_for_claim:
                    f.claim_id = claim.id
                    date_for_claim[claim.id] = f
                    break

    verifications: list[ClaimVerification] = []
    for claim in claims:
        evs = evidence_map.get(claim.id, [])
        verify_claim(claim, evs, text, finding=date_for_claim.get(claim.id), conflict_reason=reasons.get(claim.id))
        authority = unrecognized_authority(claim, evs)
        if authority:
            findings.append(
                DocumentFinding(
                    kind=FindingKind.UNRECOGNIZED_AUTHORITY,
                    severity=Severity.MEDIUM,
                    quote=authority,
                    explanation=f"'{authority}' is cited as an authority but no independent source mentions it.",
                    claim_id=claim.id,
                )
            )
        verifications.append(ClaimVerification(claim=claim, evidence=evs, verdict=claim.status.value))

    verified = sum(1 for c in claims if c.status == ClaimStatus.VERIFIED)
    contradicted = sum(1 for c in claims if c.status == ClaimStatus.CONTRADICTED)
    unverifiable = sum(1 for c in claims if c.status == ClaimStatus.UNVERIFIABLE)
    trust = compute_trust_score(claims, findings)
    risk = compute_risk_level(trust, claims, findings)

    doc_type = _detect_document_type(text)
    summary = await generate_summary(name, claims, doc_type, findings)

    return VerificationReport(
        document_name=name,
        document_type=doc_type,
        total_claims=len(claims),
        verified_count=verified,
        unverifiable_count=unverifiable,
        contradicted_count=contradicted,
        risk_level=risk,
        trust_score=trust,
        claim_verifications=verifications,
        findings=findings,
        analysis_notes=notes,
        summary=summary,
        model_tier_usage=get_usage(),
        processing_time_ms=int((time.time() - start) * 1000),
    )
