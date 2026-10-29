"""Data models for extracted claims from documents."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    UNVERIFIABLE = "unverifiable"
    CONTRADICTED = "contradicted"
    REJECTED = "rejected"


class Claim(BaseModel):
    """A single factual claim extracted from a document."""

    id: str = Field(description="Unique claim identifier")
    text: str = Field(description="The claim text as extracted")
    category: str = Field(description="Claim category: legal, financial, identity, temporal, regulatory")
    source_location: str = Field(description="Where in the document this claim appears")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence score")
    status: ClaimStatus = Field(default=ClaimStatus.PENDING)
    verification_reason: Optional[str] = Field(default=None, description="Why this status was assigned")
    entities: list[str] = Field(default_factory=list, description="Named entities in the claim")
