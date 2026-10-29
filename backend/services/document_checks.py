"""Deterministic checks on the raw document text.

Nothing in this module calls a model. These checks run on the original text of
the document, before any LLM sees it, because a model may silently normalize
what it reads (for example turning a Cyrillic look-alike letter into a Latin one).
"""

import re
import unicodedata
from urllib.parse import urlparse

from models.finding import DocumentFinding, FindingKind, Severity
from services.claim_checks import INJECTION_RES, parse_dates

# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def check_dates(text: str) -> list[DocumentFinding]:
    """Flag dates that cannot exist on a calendar (e.g. February 30)."""
    return [
        DocumentFinding(
            kind=FindingKind.INVALID_DATE,
            severity=Severity.HIGH,
            quote=m.quote,
            explanation=f"'{m.quote}' is not a real calendar date: {m.reason}.",
        )
        for m in parse_dates(text)
        if not m.ok
    ]

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
    reported_hosts: set[str] = set()
    for token in sorted(tokens, key=len):
        host = _host_of(token)
        if not host or any(host == r or host.endswith("." + r) for r in reported_hosts):
            continue
        reported_hosts.add(host)
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



def check_injection(text: str) -> list[DocumentFinding]:
    """Flag text that is addressed to an AI reviewer rather than to a human reader."""
    findings: list[DocumentFinding] = []
    seen: set[str] = set()
    for pattern in INJECTION_RES:
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
