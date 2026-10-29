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
    """A single search result and what it says about a claim."""

    source_type: EvidenceSource
    source_url: Optional[str] = Field(default=None, description="URL if from web search")
    source_title: Optional[str] = Field(default=None, description="Title of the source")
    content: str = Field(description="The snippet returned by the search")
    supports_claim: bool = Field(default=False, description="True only if stance is 'supports'")
    stance: str = Field(
        default="unjudged",
        description=(
            "supports | contradicts | irrelevant | unjudged | rejected. "
            "A model proposes supports/contradicts; the verifier sets rejected if the quote check fails."
        ),
    )
    quote: Optional[str] = Field(
        default=None,
        description="Verbatim excerpt of the snippet that the stance relies on",
    )
    relevance_score: float = Field(ge=0.0, le=1.0, description="Search engine relevance score")
    retrieved_at: str = Field(description="ISO timestamp of when evidence was retrieved")
