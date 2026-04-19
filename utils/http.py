"""
utils/http.py
─────────────
Shared HTTP client for all scrapers.

Features:
  - Automatic retries with exponential backoff (tenacity)
  - Per-request delay to avoid hammering servers
  - Rotating User-Agent headers
  - Timeout enforcement
  - Logs every request at DEBUG level

Usage:
    from utils.http import get_html, get_json

    html = get_html("https://example.com")
    data = get_json("https://api.example.com/endpoint", params={"key": "val"})
"""

from __future__ import annotations

import time
from typing import Any, Optional

import requests
from fake_useragent import UserAgent
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import MAX_RETRIES, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT

# Initialize fake user agent (falls back gracefully if unavailable)
try:
    _ua = UserAgent()
except Exception:
    _ua = None


def _get_headers() -> dict[str, str]:
    """Return request headers with a rotated User-Agent."""
    try:
        ua = _ua.random if _ua else "Mozilla/5.0 (compatible; PianoLeadFinder/1.0)"
    except Exception:
        ua = "Mozilla/5.0 (compatible; PianoLeadFinder/1.0)"
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


# ─────────────────────────────────────────────
# Retry decorator — shared across all fetch fns
# ─────────────────────────────────────────────

def _retry_decorator():
    return retry(
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=lambda state: logger.warning(
            f"Retry {state.attempt_number}/{MAX_RETRIES} for {state.args[0] if state.args else '?'}"
        ),
        reraise=True,
    )


# ─────────────────────────────────────────────
# Public fetch functions
# ─────────────────────────────────────────────

@_retry_decorator()
def get_html(
    url: str,
    params: Optional[dict] = None,
    delay: float = REQUEST_DELAY_SECONDS,
    extra_headers: Optional[dict] = None,
) -> Optional[str]:
    """
    Fetch a URL and return the HTML as a string.
    Returns None on non-retryable errors (404, etc).
    Sleeps for `delay` seconds before the request.
    """
    time.sleep(delay)
    headers = {**_get_headers(), **(extra_headers or {})}
    logger.debug(f"GET {url}")
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.HTTPError as e:
        logger.warning(f"HTTP {e.response.status_code} for {url}")
        return None


@_retry_decorator()
def get_json(
    url: str,
    params: Optional[dict] = None,
    delay: float = REQUEST_DELAY_SECONDS,
    extra_headers: Optional[dict] = None,
) -> Optional[dict | list]:
    """
    Fetch a URL and return parsed JSON.
    Returns None on errors.
    """
    time.sleep(delay)
    headers = {**_get_headers(), **(extra_headers or {})}
    logger.debug(f"GET (JSON) {url}")
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        logger.warning(f"HTTP {e.response.status_code} for {url}")
        return None
    except ValueError as e:
        logger.warning(f"JSON parse error for {url}: {e}")
        return None


def create_session(delay: float = REQUEST_DELAY_SECONDS) -> requests.Session:
    """
    Create a requests.Session with our standard headers pre-set.
    Use this for scrapers that need to maintain cookies/state.
    """
    session = requests.Session()
    session.headers.update(_get_headers())
    return session
