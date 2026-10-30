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
from services.claim_checks import detect_injection, sanitize_filename
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

MAX_CLAIMS = 25
SEARCH_CONCURRENCY = 4
# Whole-request budget for evidence gathering and Super calls. Read at call time.
TIME_BUDGET_SECONDS = 45.0
NOT_CHECKED_REASON = "Not checked within time budget"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
READ_CHUNK_BYTES = 64 * 1024
MULTIPART_OVERHEAD_BYTES = 64 * 1024

_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


async def _read_limited(request: Request, file: UploadFile) -> bytes:
    """Read the upload in chunks, stopping with 413 as soon as the limit is exceeded."""
    limit = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    too_large = HTTPException(status_code=413, detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE_MB}MB")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit + MULTIPART_OVERHEAD_BYTES:
        raise too_large
    buf = bytearray()
    while True:
        chunk = await file.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > limit:
            raise too_large
    return bytes(buf)


def _check_signature(suffix: str, content: bytes) -> None:
    """Reject files whose leading bytes do not match their extension."""
    if suffix == ".webp":
        ok = content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    elif suffix in _SIGNATURES:
        ok = any(content.startswith(sig) for sig in _SIGNATURES[suffix])
    else:
        ok = True
    if not ok:
        raise HTTPException(status_code=400, detail=f"File content does not match the {suffix} file type")

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


async def _gather_evidence(
    claims: list[Claim], timeout: float
) -> tuple[dict[str, list[Evidence]], set[str]]:
    """Search evidence for every claim, bounded by a semaphore and a time budget.

    Returns (evidence_by_claim_id, ids_not_checked). Tasks still running at the
    deadline are cancelled and their claims reported as not checked.
    """
    sem = asyncio.Semaphore(SEARCH_CONCURRENCY)

    async def one(claim: Claim) -> list[Evidence]:
        async with sem:
            return await search_evidence_for_claim(
                claim_text=claim.text, entities=claim.entities, max_results=3
            )

    tasks = {c.id: asyncio.create_task(one(c)) for c in claims}
    await asyncio.wait(tasks.values(), timeout=max(timeout, 0))
    evidence: dict[str, list[Evidence]] = {}
    unchecked: set[str] = set()
    for cid, task in tasks.items():
        if not task.done():
            task.cancel()
            unchecked.add(cid)
        elif task.cancelled() or task.exception() is not None:
            if not task.cancelled():
                logger.warning("Evidence search failed: %s", type(task.exception()).__name__)
            unchecked.add(cid)
        else:
            evidence[cid] = task.result()
    return evidence, unchecked


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
    allowed = sorted(set(ALLOWED_EXTENSIONS) | IMAGE_EXTENSIONS)
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(allowed)}",
        )
    content = await _read_limited(request, file)
    _check_signature(suffix, content)

    if suffix in IMAGE_EXTENSIONS:
        # No vision tier is wired into the pipeline; never fabricate text for an image.
        raise HTTPException(status_code=501, detail="Image analysis is not available")

    text = _extract_text(name, content)
    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the document")

    notes: list[str] = []
    findings: list[DocumentFinding] = run_document_checks(text)
    safe_name = sanitize_filename(name)
    name_hits = detect_injection(name)
    if name_hits:
        findings.append(
            DocumentFinding(
                kind=FindingKind.PROMPT_INJECTION,
                severity=Severity.HIGH,
                quote=sanitize_filename(" / ".join(name_hits)),
                explanation="The file name contains text that looks like instructions to an AI reviewer. It was ignored.",
            )
        )

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

    # Conflict detection reads only the document, so it starts now and runs alongside the
    # web searches. Its result is kept even if the slower evidence review hits the time budget.
    conflict_task = asyncio.create_task(propose_conflicts(claims, text)) if len(claims) >= 2 else None

    deadline = start + TIME_BUDGET_SECONDS
    evidence_map: dict[str, list[Evidence]] = {}
    unchecked: set[str] = set()
    if claims:
        evidence_map, unchecked = await _gather_evidence(claims, deadline - time.time())
    if unchecked:
        notes.append(f"{len(unchecked)} claim(s) were not checked within the time budget.")
    elif claims and not any(evidence_map.values()):
        notes.append("Web search returned no results (missing key or search failure). Claims are unverified.")

    checked_claims = [c for c in claims if c.id not in unchecked]
    if checked_claims:
        try:
            judge_note = await asyncio.wait_for(
                judge_evidence(checked_claims, evidence_map),
                timeout=max(deadline - time.time(), 0.1),
            )
            if judge_note:
                notes.append(judge_note)
        except asyncio.TimeoutError:
            notes.append("Model evidence review did not finish within the time budget and was skipped.")

    proposals: list[dict] = []
    if conflict_task is not None:
        try:
            # The task has been running since extraction; give it a short grace period at most.
            proposals, conflict_note = await asyncio.wait_for(
                conflict_task, timeout=max(deadline - time.time(), 10.0)
            )
            if conflict_note:
                notes.append(conflict_note)
        except asyncio.TimeoutError:
            notes.append("The cross-claim conflict check did not finish within the time budget.")

    conflicts = validate_conflicts(proposals, claims, text)
    logger.info("Conflict check: %d proposed by the model, %d accepted by the verifier", len(proposals), len(conflicts))
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
        if claim.id in unchecked and claim.status == ClaimStatus.UNVERIFIABLE:
            claim.verification_reason = NOT_CHECKED_REASON
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
    summary = await generate_summary(safe_name, claims, doc_type, findings, risk)

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
