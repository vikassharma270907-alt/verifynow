"""Main verification endpoint — the core pipeline.

Flow:
  1. Upload document (PDF, text, image)
  2. Extract text content
  3. Extract claims via Nemotron-3-Nano
  4. Search evidence via Tavily for each claim
  5. Optionally deep-analyze high-stakes claims via Nemotron-3-Super
  6. Run deterministic evidence verifier (NOT an LLM)
  7. Generate summary via Nemotron-3-Ultra (once)
  8. Return structured VerificationReport
"""

import io
import logging
import time
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException

from config import MAX_UPLOAD_SIZE_MB, ALLOWED_EXTENSIONS
from models.report import VerificationReport, ClaimVerification
from services.claim_extractor import extract_claims
from services.tavily_grounder import search_evidence_for_claim
from services.deep_analyzer import should_escalate, analyze_claim_evidence
from services.evidence_verifier import verify_claim, compute_trust_score, compute_risk_level
from services.synthesizer import generate_summary
from services.model_router import get_usage, reset_usage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["verification"])


async def _extract_text(file: UploadFile, content: bytes) -> str:
    """Extract text from uploaded file based on type."""
    suffix = Path(file.filename or "unknown.txt").suffix.lower()

    if suffix == ".pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except Exception:
            logger.exception("PDF parsing failed")
            raise HTTPException(status_code=422, detail="Failed to parse PDF file")

    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        # For images, return a placeholder — in production this would use
        # Nemotron-3-Nano-Omni or Super-VL for OCR/visual understanding
        return f"[Image file: {file.filename} — visual analysis via Nemotron Omni]"

    # Default: treat as plain text
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


@router.post("/api/verify", response_model=VerificationReport)
async def verify_document(file: UploadFile = File(...)):
    """Upload a document and receive a full verification report.

    The pipeline:
      Nano (extract) → Tavily (search) → Super (deep analyze) →
      Code verifier (deterministic) → Ultra (summarize)
    """
    start_time = time.time()
    reset_usage()

    # --- Validate upload ---
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE_MB}MB",
        )

    # --- Stage 1: Extract text ---
    document_text = await _extract_text(file, content)
    if not document_text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the document")

    # --- Stage 2: Extract claims via Nemotron-3-Nano ---
    claims = await extract_claims(document_text)
    if not claims:
        return VerificationReport(
            document_name=file.filename,
            document_type="unknown",
            total_claims=0,
            verified_count=0,
            unverifiable_count=0,
            contradicted_count=0,
            risk_level="low",
            trust_score=100.0,
            claim_verifications=[],
            summary="No verifiable claims were found in this document.",
            model_tier_usage=get_usage(),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # --- Stage 3 & 4: For each claim, search + optionally deep-analyze ---
    claim_verifications: list[ClaimVerification] = []

    for claim in claims:
        # Search for evidence via Tavily
        evidence = await search_evidence_for_claim(
            claim_text=claim.text,
            entities=claim.entities,
            max_results=3,
        )

        # Escalate to Super tier if claim is high-stakes
        if should_escalate(claim) and evidence:
            evidence = await analyze_claim_evidence(claim, evidence)

        # --- Stage 5: Deterministic verification (NO LLM) ---
        claim = verify_claim(claim, evidence, document_text)

        claim_verifications.append(
            ClaimVerification(
                claim=claim,
                evidence=evidence,
                verdict=claim.status.value,
            )
        )

    # --- Compute deterministic scores ---
    verified_count = sum(1 for cv in claim_verifications if cv.verdict == "verified")
    contradicted_count = sum(1 for cv in claim_verifications if cv.verdict == "contradicted")
    unverifiable_count = sum(1 for cv in claim_verifications if cv.verdict == "unverifiable")

    trust_score = compute_trust_score([cv.claim for cv in claim_verifications])
    risk_level = compute_risk_level(trust_score, contradicted_count)

    # --- Stage 6: Generate summary via Nemotron-3-Ultra (once) ---
    doc_type = _detect_document_type(document_text)
    summary = await generate_summary(
        document_name=file.filename,
        claims=[cv.claim for cv in claim_verifications],
        document_type=doc_type,
    )

    elapsed_ms = int((time.time() - start_time) * 1000)

    return VerificationReport(
        document_name=file.filename,
        document_type=doc_type,
        total_claims=len(claims),
        verified_count=verified_count,
        unverifiable_count=unverifiable_count,
        contradicted_count=contradicted_count,
        risk_level=risk_level,
        trust_score=trust_score,
        claim_verifications=claim_verifications,
        summary=summary,
        model_tier_usage=get_usage(),
        processing_time_ms=elapsed_ms,
    )


def _detect_document_type(text: str) -> str:
    """Simple heuristic document type detection."""
    lower = text.lower()
    if any(kw in lower for kw in ["lease", "tenant", "landlord", "rent"]):
        return "lease_agreement"
    if any(kw in lower for kw in ["invoice", "amount due", "bill to", "payment"]):
        return "invoice"
    if any(kw in lower for kw in ["contract", "agreement", "parties", "hereby"]):
        return "contract"
    if any(kw in lower for kw in ["terms of service", "privacy policy", "user agreement"]):
        return "terms_of_service"
    if any(kw in lower for kw in ["resume", "curriculum vitae", "experience", "education"]):
        return "resume"
    return "general_document"
