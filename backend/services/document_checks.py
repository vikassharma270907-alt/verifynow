"""Deterministic checks on the raw document text.

Nothing in this module calls a model. These checks run on the original text of
the document, before any LLM sees it, because a model may silently normalize
what it reads (for example turning a Cyrillic look-alike letter into a Latin one).
"""

import calendar
import re
import unicodedata
from urllib.parse import urlparse

from models.finding import DocumentFinding, FindingKind, Severity

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
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATE_NUMERIC = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")


def _valid_ymd(year: int, month: int, day: int) -> bool:
    if not (1 <= year <= 9999 and 1 <= month <= 12):
        return False
    return 1 <= day <= calendar.monthrange(year, month)[1]


def check_dates(text: str) -> list[DocumentFinding]:
    """Flag dates that cannot exist on a calendar (e.g. February 30)."""
    findings: list[DocumentFinding] = []
    seen: set[str] = set()

    def add(quote: str) -> None:
        key = quote.lower()
        if key in seen:
            return
        seen.add(key)
        findings.append(
            DocumentFinding(
                kind=FindingKind.INVALID_DATE,
                severity=Severity.HIGH,
                quote=quote,
                explanation=f"'{quote}' is not a real calendar date.",
            )
        )

    for m in _DATE_MDY.finditer(text):
        if not _valid_ymd(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2))):
            add(m.group(0))
    for m in _DATE_DMY.finditer(text):
        if not _valid_ymd(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1))):
            add(m.group(0))
    for m in _DATE_ISO.finditer(text):
        if not _valid_ymd(int(m.group(1)), int(m.group(2)), int(m.group(3))):
            add(m.group(0))
    for m in _DATE_NUMERIC.finditer(text):
        a, b, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Ambiguous between day/month and month/day: only flag if neither reading is valid.
        if not (_valid_ymd(year, a, b) or _valid_ymd(year, b, a)):
            add(m.group(0))
    return findings


# ---------------------------------------------------------------------------
# Look-alike (homograph) domains
# ---------------------------------------------------------------------------
# Characters from other scripts that render almost identically to Latin letters.
_CONFUSABLES = {
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c",
    "\u0443": "y", "\u0445": "x", "\u0456": "i", "\u0458": "j", "\u0455": "s",
    "\u0501": "d", "\u04cf": "l", "\u03bf": "o", "\u03bd": "v", "\u03b1": "a",
    "\u03b9": "i", "\u0578": "n", "\u0261": "g",
}

_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"')\]]+", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_BARE_DOMAIN = re.compile(r"[\w-]*[^\x00-\x7f][\w.-]*\.[a-z]{2,}", re.IGNORECASE)


def _host_of(token: str) -> str:
    if "@" in token and "://" not in token:
        return token.rsplit("@", 1)[1].lower()
    candidate = token if "://" in token else "//" + token
    try:
        return (urlparse(candidate).hostname or "").lower()
    except ValueError:
        return ""


def check_domains(text: str) -> list[DocumentFinding]:
    """Flag domains that use look-alike characters or punycode."""
    tokens: set[str] = set()
    for pattern in (_URL, _EMAIL, _BARE_DOMAIN):
        for m in pattern.finditer(text):
            tokens.add(m.group(0).rstrip(".,;:)"))

    findings: list[DocumentFinding] = []
    for token in sorted(tokens):
        host = _host_of(token)
        if not host:
            continue
        lookalikes = [ch for ch in host if ch in _CONFUSABLES]
        if lookalikes:
            names = sorted({f"{unicodedata.name(ch, 'UNKNOWN')} (U+{ord(ch):04X})" for ch in lookalikes})
            skeleton = "".join(_CONFUSABLES.get(ch, ch) for ch in host)
            findings.append(
                DocumentFinding(
                    kind=FindingKind.HOMOGRAPH_DOMAIN,
                    severity=Severity.HIGH,
                    quote=token,
                    explanation=(
                        f"This domain contains look-alike characters ({', '.join(names[:3])}) "
                        f"and imitates '{skeleton}'. Links like this are used to impersonate real sites."
                    ),
                )
            )
        elif "xn--" in host:
            findings.append(
                DocumentFinding(
                    kind=FindingKind.PUNYCODE_DOMAIN,
                    severity=Severity.MEDIUM,
                    quote=token,
                    explanation="This domain is encoded as punycode (xn--), which can hide look-alike characters.",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Prompt injection aimed at an AI reviewer
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
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
_INJECTION_RES = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def check_injection(text: str) -> list[DocumentFinding]:
    """Flag text that is addressed to an AI reviewer rather than to a human reader."""
    findings: list[DocumentFinding] = []
    seen: set[str] = set()
    for pattern in _INJECTION_RES:
        for m in pattern.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            line_end = len(text) if line_end == -1 else line_end
            line = text[line_start:line_end].strip()
            if len(line) > 240:
                start = max(0, m.start() - 100)
                line = "..." + text[start : m.end() + 100].strip() + "..."
            if line in seen:
                continue
            seen.add(line)
            findings.append(
                DocumentFinding(
                    kind=FindingKind.PROMPT_INJECTION,
                    severity=Severity.HIGH,
                    quote=line,
                    explanation=(
                        "Instructions aimed at an AI reviewer were found hidden in the document. "
                        "They were treated as untrusted content and ignored."
                    ),
                )
            )
    return findings


def run_document_checks(text: str) -> list[DocumentFinding]:
    """Run every deterministic document check."""
    return check_injection(text) + check_domains(text) + check_dates(text)
