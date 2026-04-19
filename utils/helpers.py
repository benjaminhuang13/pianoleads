"""
utils/helpers.py
────────────────
Pure utility functions — no imports from other project modules.
All functions are stateless and independently testable.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse


# ─────────────────────────────────────────────
# Phone
# ─────────────────────────────────────────────

# Regex to find phone-like patterns in free text
_PHONE_RE = re.compile(
    r"""
    (?:(?:\+?1[\s.\-]?))?        # optional country code
    (?:\(?\d{3}\)?[\s.\-]?)      # area code
    \d{3}[\s.\-]?\d{4}           # 7-digit number
    """,
    re.VERBOSE,
)

def extract_phones(text: str) -> list[str]:
    """Find all phone-like strings in text. Returns list of normalized phone strings."""
    matches = _PHONE_RE.findall(text)
    result = []
    for m in matches:
        normalized = normalize_phone(m)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def normalize_phone(phone: str) -> str | None:
    """Strip all non-digit characters. Return 10-digit string or None."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else None


def format_phone_display(phone: str) -> str:
    """Format a 10-digit phone string as (555) 555-5555."""
    if len(phone) != 10 or not phone.isdigit():
        return phone
    return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"


# ─────────────────────────────────────────────
# Email
# ─────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

def extract_emails(text: str) -> list[str]:
    """Find all email addresses in text."""
    return list({m.lower() for m in _EMAIL_RE.findall(text)})


# ─────────────────────────────────────────────
# URLs / domains
# ─────────────────────────────────────────────

def extract_domain(url: str) -> str | None:
    """
    Extract the bare domain from a URL.
    'https://www.janespiano.com/lessons' → 'janespiano.com'
    """
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else "https://" + url)
        domain = parsed.netloc.lower()
        return domain.lstrip("www.") if domain else None
    except Exception:
        return None


def ensure_scheme(url: str) -> str:
    """Add https:// if no scheme present."""
    if url and not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def is_same_domain(url1: str, url2: str) -> bool:
    """Return True if both URLs resolve to the same domain."""
    return bool(
        extract_domain(url1)
        and extract_domain(url1) == extract_domain(url2)
    )


def resolve_url(base: str, relative: str) -> str:
    """Resolve a relative URL against a base URL."""
    return urljoin(base, relative)


def extract_links(html: str, base_url: str) -> list[str]:
    """
    Extract all <a href> links from HTML, resolved against base_url.
    Returns only http/https links.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        full = resolve_url(base_url, href)
        if full.startswith(("http://", "https://")):
            links.append(full)
    return links


# ─────────────────────────────────────────────
# Text cleaning
# ─────────────────────────────────────────────

def clean_text(text: str | None) -> str | None:
    """Collapse whitespace and strip leading/trailing spaces."""
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def title_case_name(name: str | None) -> str | None:
    """Normalize a name to title case, handling common edge cases."""
    if not name:
        return None
    return name.strip().title() or None


# ─────────────────────────────────────────────
# ZIP code helpers
# ─────────────────────────────────────────────

def extract_zip_from_address(address: str) -> str | None:
    """Pull a 5-digit ZIP code from an address string."""
    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", address or "")
    return match.group(1) if match else None
