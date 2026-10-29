"""Data models for evidence collected during verification."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EvidenceSource(str, Enum):
    TAVILY_SEARCH = "tavily_search"
    DOCUMENT_QUOTE = "document_quote"
    REGULATORY_DB = "regulatory_db"
    DETERMINISTIC_CHECK = "deterministic_check"


class Evidence(BaseModel):
    """A single piece of evidence supporting or contradicting a claim."""

    source_type: EvidenceSource
    source_url: Optional[str] = Field(default=None, description="URL if from web search")
    source_title: Optional[str] = Field(default=None, description="Title of the source")
    content: str = Field(description="The evidence content or quote")
    supports_claim: bool = Field(description="True if evidence supports the claim, False if contradicts")
    relevance_score: float = Field(ge=0.0, le=1.0, description="How relevant this evidence is")
    retrieved_at: str = Field(description="ISO timestamp of when evidence was retrieved")
