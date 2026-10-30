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
    needs_outside_evidence,
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
# Vercel caps the function at 60 s (vercel.json maxDuration); 50 s leaves room for the
# Ultra summary (2-3 s measured). Override with VERIFY_TIME_BUDGET_SECONDS.
TIME_BUDGET_SECONDS = float(os.environ.get("VERIFY_TIME_BUDGET_SECONDS", "50"))
# Extraction must finish this many seconds before the budget ends, leaving time for search and judging.
EXTRACTION_RESERVE_SECONDS = 10.0
# Hard stop for the whole request (Vercel kills the function at 60 s). The summary only
# uses whatever time remains before this point, otherwise the template is used.
HARD_LIMIT_SECONDS = 56.0
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

# Forwarded-IP headers are client-controlled unless a trusted proxy sets them.
# Vercel overwrites them, so they are trusted there; elsewhere set TRUST_PROXY_HEADERS=1
# only when running behind a proxy that does the same.
TRUST_PROXY_HEADERS = bool(os.environ.get("VERCEL")) or os.environ.get("TRUST_PROXY_HEADERS") == "1"
MAX_PDF_PAGES = int(os.environ.get("MAX_PDF_PAGES", "50"))


def _client_id(request: Request) -> str:
    """Identify the caller for rate limiting without trusting a spoofable left-most XFF value."""
    if TRUST_PROXY_HEADERS:
        for header in ("x-vercel-forwarded-for", "x-real-ip"):
            value = request.headers.get(header, "").strip()
            if value:
                return value.split(",")[-1].strip()[:64]
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if parts:
            return parts[-1][:64]  # right-most entry was appended by our own proxy
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request) -> None:
    if RATE_LIMIT_PER_HOUR <= 0:
        return
    client = _client_id(request)
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
            if len(reader.pages) > MAX_PDF_PAGES:
                raise HTTPException(status_code=413, detail=f"PDF has too many pages. Maximum: {MAX_PDF_PAGES}")
            return "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except HTTPException:
            raise
        except Exception:
            logger.exception("PDF parsing failed")
            raise HTTPException(status_code=422, detail="Failed to parse PDF file") from None
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
    try:
        await asyncio.wait(tasks.values(), timeout=max(timeout, 0))
    finally:
        # Runs on deadline and on outer cancellation (client disconnect): stop stragglers
        # and wait for them so no task is left pending or with an unretrieved exception.
        pending = [t for t in tasks.values() if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    evidence: dict[str, list[Evidence]] = {}
    unchecked: set[str] = set()
    for cid, task in tasks.items():
        if task.cancelled():
            unchecked.add(cid)
        elif (exc := task.exception()) is not None:
            logger.warning("Evidence search failed: %s", type(exc).__name__)
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

    # PDF parsing is CPU-bound; keep it off the event loop.
    text = await asyncio.to_thread(_extract_text, name, content)
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

    # Conflict detection reads only the document, so it starts before claim extraction and
    # runs alongside extraction and the web searches. Its quotes are mapped to claims later.
    conflict_task: asyncio.Task | None = asyncio.create_task(propose_conflicts(None, text))

    try:
        # Extraction gets the budget minus room for search/judging; a stalled call must not
        # carry the request past the serverless limit.
        extraction_timeout = max(start + TIME_BUDGET_SECONDS - EXTRACTION_RESERVE_SECONDS - time.time(), 5.0)
        claims = (await asyncio.wait_for(extract_claims(text), timeout=extraction_timeout))[:MAX_CLAIMS]
    except BaseException as exc:
        # BaseException so the conflict task is also cleaned up on client disconnect
        # (CancelledError), which is re-raised below.
        conflict_task.cancel()
        await asyncio.gather(conflict_task, return_exceptions=True)
        if isinstance(exc, asyncio.TimeoutError):
            logger.error("Claim extraction timed out after %.0fs", extraction_timeout)
            raise HTTPException(status_code=504, detail="Claim extraction timed out. Please try again.") from None
        if isinstance(exc, UpstreamError):
            logger.error("Claim extraction upstream error: status=%s", exc.status)
            raise HTTPException(status_code=exc.status, detail=exc.safe_message) from None
        if isinstance(exc, Exception):
            logger.exception("Claim extraction failed")
            raise HTTPException(status_code=502, detail="Claim extraction failed") from None
        raise

    if not claims:
        notes.append("No verifiable claims were extracted from this document.")

    try:
        deadline = start + TIME_BUDGET_SECONDS
        evidence_map: dict[str, list[Evidence]] = {}
        unchecked: set[str] = set()
        # Claims about the document itself, or with no named subject, can never be verified by a
        # web source, so they skip searching and model review (saves time budget and tokens).
        searchable = [c for c in claims if needs_outside_evidence(c)]
        if searchable:
            evidence_map, unchecked = await _gather_evidence(searchable, deadline - time.time())
        if unchecked:
            notes.append(f"{len(unchecked)} claim(s) were not checked within the time budget.")
        elif searchable and not any(evidence_map.values()):
            notes.append("Web search returned no results (missing key or search failure). Claims are unverified.")

        checked_claims = [c for c in searchable if c.id not in unchecked]
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
                # The task has been running in parallel since before extraction. Wait only
                # for whatever remains of the time budget (with a small floor) so a slow
                # conflict call cannot push the request past the serverless limit.
                proposals, conflict_note = await asyncio.wait_for(
                    conflict_task, timeout=max(deadline - time.time(), 0.5)
                )
                if conflict_note:
                    notes.append(conflict_note)
            except asyncio.TimeoutError:
                notes.append("The cross-claim conflict check did not finish within the time budget.")
    finally:
        # Client disconnect or an unexpected error must not leave the conflict call running.
        # Always await it (even when already done) so an exception is never left unretrieved.
        if conflict_task is not None:
            if not conflict_task.done():
                conflict_task.cancel()
            await asyncio.gather(conflict_task, return_exceptions=True)

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
                # Attach to whichever side matched a claim, so the penalty is not counted twice.
                claim_id=c.claim_a or c.claim_b,
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
    summary = await generate_summary(
        safe_name, claims, doc_type, findings, risk,
        timeout=max(start + HARD_LIMIT_SECONDS - time.time(), 0.5),
    )

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
