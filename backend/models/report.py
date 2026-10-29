"""Data models for the final verification report."""

from enum import Enum

from pydantic import BaseModel, Field

from .claim import Claim
from .evidence import Evidence
from .finding import DocumentFinding


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClaimVerification(BaseModel):
    """A claim paired with its collected evidence and final verdict."""

    claim: Claim
    evidence: list[Evidence] = Field(default_factory=list)
    verdict: str = Field(description="Final determination: verified, unverifiable, contradicted")


class VerificationReport(BaseModel):
    """The complete verification report for a document."""

    document_name: str
    document_type: str = Field(description="Detected document type: contract, legal, financial, etc.")
    total_claims: int
    verified_count: int
    unverifiable_count: int
    contradicted_count: int
    risk_level: RiskLevel
    trust_score: float = Field(ge=0.0, le=100.0, description="Overall trust percentage")
    claim_verifications: list[ClaimVerification] = Field(default_factory=list)
    findings: list[DocumentFinding] = Field(default_factory=list)
    analysis_notes: list[str] = Field(
        default_factory=list,
        description="Anything that limited the analysis (a model call failed, search returned nothing, ...)",
    )
    summary: str = Field(description="Human-readable summary of findings")
    model_tier_usage: dict[str, int] = Field(
        default_factory=dict,
        description="Token count per model tier: nano, super, ultra",
    )
    processing_time_ms: int = Field(description="Total processing time in milliseconds")
