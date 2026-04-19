"""
config/settings.py
──────────────────
Central configuration. All tunable values live here.
Load with: from config.settings import settings
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────

ROOT_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
LOG_DIR    = ROOT_DIR / "logs"

OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# API Keys
# ─────────────────────────────────────────────

GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ─────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────

LEADS_DB_PATH: Path = Path(os.getenv("LEADS_DB_PATH", str(OUTPUT_DIR / "leads.json")))

# ─────────────────────────────────────────────
# HTTP / scraper behavior
# ─────────────────────────────────────────────

REQUEST_DELAY_SECONDS: float = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5"))
MAX_RETRIES: int              = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT: int          = int(os.getenv("REQUEST_TIMEOUT", "10"))

# ─────────────────────────────────────────────
# Google Maps scraper
# ─────────────────────────────────────────────

# Max results per search query (Google Places returns max 60 via pagination)
GMAPS_MAX_RESULTS_PER_QUERY: int = 60

# Search terms to use for each territory
GMAPS_SEARCH_TERMS: list[str] = [
    "piano teacher",
    "piano lessons",
    "piano studio",
    "piano instruction",
]

# ─────────────────────────────────────────────
# Domain crawler
# ─────────────────────────────────────────────

# Keywords that identify a site as a piano teacher site
PIANO_KEYWORDS: list[str] = [
    "piano lessons",
    "piano teacher",
    "piano studio",
    "piano instruction",
    "learn piano",
    "piano class",
    "keyboard lessons",
]

# How many pages deep to crawl from a domain's homepage
CRAWL_MAX_DEPTH: int = 2

# Max pages to visit per domain (safety limit)
CRAWL_MAX_PAGES: int = 10

# ─────────────────────────────────────────────
# Enrichment
# ─────────────────────────────────────────────

# Flag domains newer than this many days as "new/interesting"
NEW_DOMAIN_THRESHOLD_DAYS: int = 365

# ─────────────────────────────────────────────
# Confidence scoring weights
# (used in processors/enricher.py)
# ─────────────────────────────────────────────

CONFIDENCE_WEIGHTS = {
    "has_phone":           2,
    "has_website":         1,
    "has_email":           1,
    "has_rating":          1,
    "review_count_10plus": 1,
    "review_count_50plus": 1,   # stacks with above
    "multiple_sources":    2,   # seen in 2+ sources
    "has_photo":           1,
}
# Max possible score = sum of all weights = 10
