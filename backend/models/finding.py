"""Deterministic document-level findings (produced by code, not by models)."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class FindingKind(str, Enum):
    INVALID_DATE = "INVALID_DATE"
    HOMOGRAPH_DOMAIN = "HOMOGRAPH_DOMAIN"
    PUNYCODE_DOMAIN = "PUNYCODE_DOMAIN"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    INTERNAL_CONFLICT = "INTERNAL_CONFLICT"
    UNRECOGNIZED_AUTHORITY = "UNRECOGNIZED_AUTHORITY"


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class DocumentFinding(BaseModel):
    kind: FindingKind
    severity: Severity
    quote: str
    explanation: str
    claim_id: Optional[str] = None
