"""Pure deterministic helpers shared by the verifier, grounder and extractors.

No network, no LLM, no file I/O. Nothing here is allowed to import model_router.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
_MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))

_DATE_MDY = re.compile(
    rf"\b({_MONTH_ALT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.IGNORECASE
)
_DATE_DMY = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_ALT})\.?,?\s+(\d{{4}})\b", re.IGNORECASE
)
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_DATE_NUMERIC = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")


@dataclass(frozen=True)
class DateMention:
    quote: str
    ok: bool
    reason: str  # empty when ok
    value: Optional[date]


def _invalid_reason(year: int, month: int, day: int) -> str:
    """Explain why year/month/day is not a real date. Returns '' if it is real."""
    if not 1 <= year <= 9999:
        return f"Year {year} is out of range"
    if not 1 <= month <= 12:
        return f"Month {month} does not exist"
    last = calendar.monthrange(year, month)[1]
    if 1 <= day <= last:
        return ""
    name = calendar.month_name[month]
    if month == 2 and day == 29:
        return f"February 29 does not exist because {year} is not a leap year"
    if day < 1:
        return f"Day {day} does not exist in {name}"
    return f"{name} {day} does not exist ({name} only has {last} days in {year})"


def _check_ymd(quote: str, year: int, month: int, day: int) -> DateMention:
    reason = _invalid_reason(year, month, day)
    if reason:
        return DateMention(quote, False, reason, None)
    return DateMention(quote, True, "", date(year, month, day))


def _check_numeric(quote: str, a: int, b: int, year: int) -> DateMention:
    """a/b/year may be month/day (US) or day/month (European); valid in either is ok."""
    us = _check_ymd(quote, year, a, b)
    if us.ok:
        return us
    eu = _check_ymd(quote, year, b, a)
    if eu.ok:
        return eu
    # Neither reading works: explain using the most plausible reading.
    return us if a <= 12 or b > 12 else eu


def parse_dates(text: str) -> list[DateMention]:
    """Find date mentions in text and validate each against the real calendar."""
    out: list[DateMention] = []
    seen: set[str] = set()

    def add(m: DateMention) -> None:
        key = m.quote.lower()
        if key not in seen:
            seen.add(key)
            out.append(m)

    for m in _DATE_MDY.finditer(text):
        add(_check_ymd(m.group(0), int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2))))
    for m in _DATE_DMY.finditer(text):
        add(_check_ymd(m.group(0), int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1))))
    for m in _DATE_ISO.finditer(text):
        add(_check_ymd(m.group(0), int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in _DATE_NUMERIC.finditer(text):
        add(_check_numeric(m.group(0), int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return out


def validate_date(text: str) -> tuple[bool, str]:
    """Validate a single date string. Returns (ok, reason); reason is '' when ok.

    Unrecognised formats return (False, 'Unrecognised date format').
    """
    mentions = parse_dates(text.strip())
    if not mentions:
        return False, "Unrecognised date format"
    for m in mentions:
        if not m.ok:
            return False, m.reason
    return True, ""


# ---------------------------------------------------------------------------
# Numbers and agreement
# ---------------------------------------------------------------------------
_NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def extract_numbers(text: str) -> list[float]:
    """Extract numeric values, normalising thousands commas and currency symbols."""
    values: list[float] = []
    for m in _NUMBER.finditer(text or ""):
        raw = m.group(0).rstrip(",").replace(",", "")
        try:
            values.append(float(raw))
        except ValueError:
            continue
    return values


_STOPWORDS = frozenset(
    "the and for with that this from are was were has have had will shall per not but its "
    "their there been being into than then also any all may can who whom which when where".split()
)
_WORD = re.compile(r"[a-z][a-z'-]+")
OVERLAP_THRESHOLD = 0.6


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if len(w) > 2 and w not in _STOPWORDS}


def agreement(claim: str, content: str) -> str:
    """Deterministically compare a claim to evidence text.

    Returns 'supports', 'conflicts' or 'neutral'. Unrelated text is always neutral.
    """
    claim_tokens = _tokens(claim)
    if not claim_tokens:
        return "neutral"
    overlap = len(claim_tokens & _tokens(content)) / len(claim_tokens)
    if overlap < OVERLAP_THRESHOLD:
        return "neutral"
    claim_nums = set(extract_numbers(claim))
    if not claim_nums:
        return "supports"
    content_nums = set(extract_numbers(content))
    if claim_nums <= content_nums:
        return "supports"
    if content_nums:
        return "conflicts"
    return "neutral"


# ---------------------------------------------------------------------------
# Prompt injection (detection only; never changes a verdict)
# ---------------------------------------------------------------------------
INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts?|rules)",
    r"disregard\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts?|rules)",
    r"mark\s+(?:all\s+|every\s+|each\s+)?(?:claims?|findings?|items?)\s+as\s+(?:verified|true|safe|valid)",
    r"(?:do\s+not|don'?t)\s+flag\s+(?:any|anything)",
    r"you\s+are\s+now\s+(?:a|an|in)\b",
    r"(?:system|developer)\s+prompt",
    r"(?:this|the)\s+document\s+is\s+(?:completely\s+)?(?:safe|verified|trusted|authentic)",
    r"with\s+100%\s+confidence",
    r"override\s+(?:the\s+)?(?:verification|safety|security)",
]
INJECTION_RES = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def detect_injection(text: str) -> list[str]:
    """Return the distinct phrases in text that look like instructions to an AI reviewer."""
    found: list[str] = []
    for pattern in INJECTION_RES:
        for m in pattern.finditer(text or ""):
            phrase = m.group(0)
            if phrase not in found:
                found.append(phrase)
    return found


# ---------------------------------------------------------------------------
# Filenames and categories
# ---------------------------------------------------------------------------
_UNSAFE_CHARS = re.compile(r"[^\w.\- ]", re.UNICODE)
MAX_FILENAME_LEN = 100


def sanitize_filename(name: object) -> str:
    """Reduce a user-supplied filename to a short, single-line, prompt-safe string."""
    if not isinstance(name, str):
        return "document"
    base = re.split(r"[\\/]", name)[-1]
    base = _UNSAFE_CHARS.sub("_", base).strip(" ._")
    base = re.sub(r"\s+", " ", base)[:MAX_FILENAME_LEN]
    return base or "document"


VALID_CATEGORIES = ("legal", "financial", "identity", "temporal", "regulatory", "factual")


def normalize_category(value: object) -> str:
    """Map any model-provided category to the known set; default 'factual'."""
    if isinstance(value, str):
        v = value.strip().lower()
        if v in VALID_CATEGORIES:
            return v
    return "factual"
