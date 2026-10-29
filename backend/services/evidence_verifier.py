"""Deterministic evidence verifier: the trust gate.

This module makes every verification decision and contains NO model calls.
Models upstream may PROPOSE a stance on a snippet or a conflict between two
statements; a proposal only counts if it passes the checks below:

  * it cites a verbatim quote that really appears in the snippet / document
  * the quote mentions the claim's named entity (so unrelated snippets cannot verify it)
  * the document is never its own evidence: a claim that only appears in the
    document is reported as "stated in the document", not as verified.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from models.claim import Claim, ClaimStatus
from models.evidence import Evidence
from models.finding import DocumentFinding, FindingKind, Severity

# Thresholds are fixed constants, not learned.
EVIDENCE_RELEVANCE_THRESHOLD = 0.5
MIN_QUOTE_CHARS = 12
UNVERIFIABLE_CREDIT = 0.35
PENALTY_CONTRADICTED = 30.0
PENALTY_HIGH_FINDING = 25.0
PENALTY_MEDIUM_FINDING = 10.0

# A report with zero claims verified nothing: neutral score, never "low" risk.
EMPTY_REPORT_TRUST_SCORE = 50.0
EMPTY_REPORT_RISK_LEVEL = "medium"
EMPTY_REPORT_SUMMARY = (
    "No verifiable claims were extracted from this document, so nothing was verified. "
    "This is not a clean bill of health."
)

_STOPWORDS = {
    "agreement", "parties", "party", "shall", "under", "which", "there", "their",
    "after", "before", "between", "these", "those", "would", "could", "other",
    "about", "within", "without", "being", "document", "contract",
}

_AUTHORITY_VERB = re.compile(
    r"\b(?:certified|accredited|licensed|approved|authori[sz]ed|regulated|issued)\s+(?:by|under)\b",
    re.IGNORECASE,
)
_AUTHORITY_NOUN = re.compile(
    r"\b(?:Act|Bureau|Commission|Agency|Authority|Administration|Department|Council|Institute|Ministry)\b"
)


@dataclass(frozen=True)
class Conflict:
    claim_a: str
    claim_b: str
    quote_a: str
    quote_b: str
    reason: str


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def _norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def quote_in(quote: str | None, text: str | None) -> bool:
    """True if the quote appears verbatim (ignoring case and whitespace) in the text."""
    q = _norm(quote).strip(" .\"'")
    return len(q) >= MIN_QUOTE_CHARS and q in _norm(text)


def _anchors(claim: Claim) -> list[str]:
    """Names a supporting source must mention: the claim's entities, else its key words."""
    found: set[str] = set()
    for entity in claim.entities:
        e = _norm(entity)
        if len(e) >= 3:
            found.add(e)
        for m in re.finditer(r"\(([^)]{2,})\)", e):
            found.add(m.group(1).strip())
        base = re.sub(r"\([^)]*\)", "", e).strip()
        if len(base) >= 3:
            found.add(base)
    if found:
        return sorted(found)
    words = {w for w in re.findall(r"[a-z0-9$%]{5,}", _norm(claim.text)) if w not in _STOPWORDS}
    return sorted(words)[:6]


def _anchor_in(anchors: list[str], text: str | None) -> bool:
    blob = _norm(text)
    return any(a in blob for a in anchors)


# Words that make an entity a number, date or measurement rather than a named subject.
_NON_SUBJECT_WORDS = {
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug",
    "sep", "sept", "oct", "nov", "dec", "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday", "usd", "eur", "gbp", "dollar", "dollars", "euro",
    "euros", "percent", "million", "billion", "thousand", "hour", "hours", "day", "days",
    "week", "weeks", "month", "months", "year", "years", "pdt", "pst", "utc", "est",
    "cst", "gmt", "metre", "metres", "meter", "meters", "feet", "foot", "mile", "miles",
    "kilometre", "kilometres", "kilometer", "kilometers", "kilogram", "kilograms", "pound",
    "pounds", "ton", "tons", "tonne", "tonnes", "acre", "acres",
}


def _subject_anchors(claim: Claim, anchors: list[str]) -> list[str]:
    """Anchors that name what the claim is about: proper nouns, not numbers, dates or generic phrases.

    An entity counts only if it contains a capitalized word, is not just a date or unit, and is
    not merely the capitalized first word of the claim ("Projects must..."). Generic phrases such
    as "grand prize" appear in unrelated pages and must not anchor a claim to a source.
    Without entities, the claim's key words stand in.
    """
    if not claim.entities:
        return anchors
    first = re.findall(r"[A-Za-z0-9$%]+", claim.text)[:1]
    first_word = first[0].lower() if first else ""
    subjects: list[str] = []
    for entity in claim.entities:
        words = re.findall(r"[A-Za-z][A-Za-z0-9&.'-]*", entity)
        if not words or not any(w[0].isupper() for w in words):
            continue
        if all(w.lower() in _NON_SUBJECT_WORDS for w in words):
            continue
        if len(words) == 1 and words[0].lower() == first_word:
            continue
        subjects.append(_norm(entity))
    return subjects


def _qualifies(ev: Evidence, stance: str, anchors: list[str], subjects: list[str] | None = None) -> bool:
    if not (
        ev.stance == stance
        and ev.relevance_score >= EVIDENCE_RELEVANCE_THRESHOLD
        and bool(ev.quote)
        and quote_in(ev.quote, ev.content)
        and _anchor_in(anchors, ev.quote)
    ):
        return False
    # The snippet must be about the claim's subject. A quote that only repeats the same
    # number from some other context (another contest's "$5,000 grand prize") must not count.
    return not subjects or _anchor_in(subjects, f"{ev.source_title or ''} {ev.content}")


def _hosts(evidence: list[Evidence]) -> str:
    names: list[str] = []
    for ev in evidence[:3]:
        host = ""
        if ev.source_url:
            try:
                host = urlparse(ev.source_url).hostname or ""
            except ValueError:
                host = ""
        names.append(host or ev.source_title or "source")
    return ", ".join(dict.fromkeys(names))


# ---------------------------------------------------------------------------
# Per-claim verdict
# ---------------------------------------------------------------------------
def verify_claim(
    claim: Claim,
    evidence: list[Evidence],
    document_text: str,
    finding: DocumentFinding | None = None,
    conflict_reason: str | None = None,
) -> Claim:
    """Decide a claim's status from deterministic rules. Mutates and returns the claim."""
    anchors = _anchors(claim)
    subjects = _subject_anchors(claim, anchors)
    # Entities exist but none names a subject (only numbers or dates): the claim does not say
    # what it is about, so no outside source can confirm or refute it.
    unnamed = bool(claim.entities) and not subjects

    # Proposals that fail the quote/entity gate are marked rejected so the UI can show why.
    for ev in evidence:
        if ev.stance in ("supports", "contradicts") and (
            unnamed or not _qualifies(ev, ev.stance, anchors, subjects)
        ):
            ev.stance = "rejected"
            ev.supports_claim = False

    # 1. Deterministic document findings (impossible date, ...)
    if finding is not None:
        claim.status = ClaimStatus.CONTRADICTED
        claim.verification_reason = finding.explanation
        return claim

    # 2. Internal conflict with another statement in the same document
    if conflict_reason:
        claim.status = ClaimStatus.CONTRADICTED
        claim.verification_reason = conflict_reason
        return claim

    if unnamed:
        claim.status = ClaimStatus.UNVERIFIABLE
        claim.verification_reason = (
            "This claim does not say what it is about, so an outside source cannot confirm it."
        )
        return claim

    contradicting = [ev for ev in evidence if _qualifies(ev, "contradicts", anchors, subjects)]
    supporting = [ev for ev in evidence if _qualifies(ev, "supports", anchors, subjects)]

    # 3. Independent evidence against the claim
    if contradicting:
        claim.status = ClaimStatus.CONTRADICTED
        claim.verification_reason = f"Contradicted by {len(contradicting)} source(s): {_hosts(contradicting)}"
        return claim

    # 4. Independent evidence for the claim
    if supporting:
        claim.status = ClaimStatus.VERIFIED
        claim.verification_reason = f"Supported by {len(supporting)} independent source(s): {_hosts(supporting)}"
        return claim

    # 5. Nothing independent. The document cannot vouch for itself.
    claim.status = ClaimStatus.UNVERIFIABLE
    if any(ev.stance == "unjudged" for ev in evidence):
        claim.verification_reason = "Search results were found but could not be assessed."
    elif _anchor_in(anchors, document_text):
        claim.verification_reason = "Stated in the document only. No independent source confirmed it."
    else:
        claim.verification_reason = "No independent evidence found."
    return claim


def unrecognized_authority(claim: Claim, evidence: list[Evidence]) -> str | None:
    """Name of a certifying body / law the claim cites that no independent source mentions.

    Only applies to unverifiable claims that cite an authority. Returns None otherwise.
    """
    if claim.status != ClaimStatus.UNVERIFIABLE or not evidence:
        return None
    if not (_AUTHORITY_VERB.search(claim.text) or _AUTHORITY_NOUN.search(claim.text)):
        return None
    anchors = _anchors(claim)
    if not anchors:
        return None
    blob = _norm(" ".join(ev.content for ev in evidence))
    if any(a in blob for a in anchors):
        return None
    # Report the entity that actually names the authority, not a date or amount.
    for entity in claim.entities:
        if _AUTHORITY_NOUN.search(entity):
            return entity
    return None


# ---------------------------------------------------------------------------
# Internal conflicts between statements
# ---------------------------------------------------------------------------
def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]{4,}", _norm(text)) if w not in _STOPWORDS}


def validate_conflicts(
    proposals: list[dict], claims: list[Claim], document_text: str, limit: int = 5
) -> list[Conflict]:
    """Keep only proposed conflicts whose quotes really appear in the document.

    Both quotes must be verbatim document text, must differ, and must share a subject word.
    """
    ids = {c.id for c in claims}
    accepted: list[Conflict] = []
    seen: set[frozenset] = set()
    for p in proposals or []:
        if not isinstance(p, dict):
            continue
        a, b = p.get("claim_a"), p.get("claim_b")
        qa, qb = str(p.get("quote_a", "")), str(p.get("quote_b", ""))
        if a not in ids or b not in ids or a == b:
            continue
        if _norm(qa) == _norm(qb):
            continue
        if not (quote_in(qa, document_text) and quote_in(qb, document_text)):
            continue
        if not (_stems(qa) & _stems(qb)):
            continue
        key = frozenset((a, b))
        if key in seen:
            continue
        seen.add(key)
        reason = str(p.get("reason", "")).strip()[:300] or "The two statements cannot both be true."
        accepted.append(Conflict(a, b, qa.strip(), qb.strip(), reason))
        if len(accepted) >= limit:
            break
    return accepted


def conflict_reasons(conflicts: list[Conflict]) -> dict[str, str]:
    """Map claim id -> explanation, for both sides of every conflict."""
    out: dict[str, str] = {}
    for c in conflicts:
        out.setdefault(c.claim_a, f'Conflicts with another statement in this document: "{c.quote_b}". {c.reason}')
        out.setdefault(c.claim_b, f'Conflicts with another statement in this document: "{c.quote_a}". {c.reason}')
    return out


# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------
def _counts_separately(f: DocumentFinding) -> bool:
    """Findings already reflected in a contradicted claim must not be penalized twice."""
    reflected = f.kind in (FindingKind.INVALID_DATE, FindingKind.INTERNAL_CONFLICT) and f.claim_id is not None
    return not reflected


def _finding_counts(findings: list[DocumentFinding]) -> tuple[int, int]:
    high = sum(1 for f in findings if _counts_separately(f) and f.severity == Severity.HIGH)
    medium = sum(1 for f in findings if _counts_separately(f) and f.severity == Severity.MEDIUM)
    return high, medium


def compute_trust_score(claims: list[Claim], findings: list[DocumentFinding]) -> float:
    """Trust score 0-100 from verdict counts and document findings. Pure arithmetic."""
    n = len(claims)
    verified = sum(1 for c in claims if c.status == ClaimStatus.VERIFIED)
    unverifiable = sum(1 for c in claims if c.status == ClaimStatus.UNVERIFIABLE)
    contradicted = sum(1 for c in claims if c.status == ClaimStatus.CONTRADICTED)
    high, medium = _finding_counts(findings)

    if n == 0:
        # Nothing was checked, so nothing can be trusted. Findings still lower the score.
        base = EMPTY_REPORT_TRUST_SCORE
    else:
        base = 100.0 * (verified + UNVERIFIABLE_CREDIT * unverifiable) / n
    penalty = PENALTY_CONTRADICTED * contradicted + PENALTY_HIGH_FINDING * high + PENALTY_MEDIUM_FINDING * medium
    return round(max(0.0, min(100.0, base - penalty)), 1)


def compute_risk_level(trust_score: float, claims: list[Claim], findings: list[DocumentFinding]) -> str:
    """Risk level from contradictions and findings. Unverifiable alone is medium, not alarming."""
    contradicted = sum(1 for c in claims if c.status == ClaimStatus.CONTRADICTED)
    high, medium = _finding_counts(findings)
    if (high >= 1 and contradicted >= 1) or contradicted >= 3:
        return "critical"
    if high >= 1 or contradicted >= 1 or medium >= 2:
        return "high"
    if not claims:
        return EMPTY_REPORT_RISK_LEVEL
    if trust_score < 75:
        return "medium"
    return "low"
