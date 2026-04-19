"""
storage/schema.py
─────────────────
The single source of truth for what a Lead looks like in this system.

All scrapers produce RawLead dicts. The Normalizer converts them into
validated Lead objects. Nothing gets written to disk without passing
through this schema.

Design rules:
  - Every field has a default so partial data is always valid.
  - Enums prevent typos in status/source/territory values.
  - Use LeadStatus, SourceType, Territory everywhere — never raw strings.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────
# Enums — use these everywhere, not raw strings
# ─────────────────────────────────────────────

class LeadStatus(str, Enum):
    NEW        = "new"
    CONTACTED  = "contacted"
    QUALIFIED  = "qualified"
    CLOSED     = "closed"
    TAKEN      = "taken"       # claimed by a rep, removed from active queue


class SourceType(str, Enum):
    GOOGLE_MAPS    = "google_maps"
    GOOGLE_SEARCH  = "google_search"
    RCM            = "rcm"              # Royal Conservatory of Music
    MTNA           = "mtna"             # Music Teachers National Association
    CONSERVATORY   = "conservatory"     # local conservatories / community schools
    YOUTUBE        = "youtube"
    FACEBOOK       = "facebook"
    INSTAGRAM      = "instagram"
    THUMBTACK      = "thumbtack"
    YELP           = "yelp"
    DOMAIN_CRAWL   = "domain_crawl"
    MANUAL         = "manual"           # hand-entered by a rep


class Territory(str, Enum):
    NYC_METRO    = "nyc_metro"
    LONG_ISLAND  = "long_island"
    NORTH_JERSEY = "north_jersey"


# ─────────────────────────────────────────────
# Main Lead model
# ─────────────────────────────────────────────

class Lead(BaseModel):
    """
    A single piano teacher / studio lead.

    Required fields at creation: source, territory.
    Everything else is optional because scrapers will have partial data.
    The enricher fills in fields like domain_age_days after initial save.
    """

    # ── Identity ──────────────────────────────
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Auto-generated UUID. Never changes after creation.",
    )

    # ── Contact info ──────────────────────────
    teacher_name: Optional[str]   = None
    studio_name: Optional[str]    = None
    phone: Optional[str]          = None   # normalized: digits only, e.g. "5165551234"
    email: Optional[str]          = None
    website: Optional[str]        = None   # full URL including scheme
    address: Optional[str]        = None
    zip_code: Optional[str]       = None

    # ── Classification ────────────────────────
    source: SourceType
    territory: Territory

    # ── Google Maps / review data ─────────────
    google_place_id: Optional[str]   = None
    rating: Optional[float]          = None   # 1.0–5.0
    review_count: Optional[int]      = None
    most_recent_review: Optional[datetime] = None
    photo_count: Optional[int]       = None

    # ── Domain intelligence ───────────────────
    domain_created: Optional[datetime] = None
    domain_age_days: Optional[int]     = None   # computed from domain_created

    # ── CRM / workflow ────────────────────────
    status: LeadStatus    = LeadStatus.NEW
    assigned_to: Optional[str] = None   # rep name or ID
    notes: Optional[str]       = None

    # ── Deduplication ─────────────────────────
    duplicate_of: Optional[str] = None   # ID of the canonical lead this dupes
    sources: list[SourceType]   = Field(
        default_factory=list,
        description="All sources this lead has been seen in (grows over time).",
    )

    # ── Scoring ───────────────────────────────
    confidence_score: Optional[int] = Field(
        default=None,
        ge=1, le=10,
        description="1–10. Higher = more data points, more sources, stronger signal.",
    )

    # ── Timestamps ────────────────────────────
    found_at: datetime    = Field(default_factory=datetime.utcnow)
    updated_at: datetime  = Field(default_factory=datetime.utcnow)

    # ─────────────────────────────────────────
    # Validators
    # ─────────────────────────────────────────

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: Optional[str]) -> Optional[str]:
        """Strip everything except digits. Store as 10-digit string."""
        if v is None:
            return None
        digits = "".join(c for c in str(v) if c.isdigit())
        # Drop leading country code 1 if present and result is 11 digits
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        return digits if len(digits) == 10 else None

    @field_validator("website", mode="before")
    @classmethod
    def normalize_website(cls, v: Optional[str]) -> Optional[str]:
        """Ensure website has a scheme."""
        if v is None:
            return None
        v = v.strip()
        if v and not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v or None

    @field_validator("rating", mode="before")
    @classmethod
    def clamp_rating(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        return max(1.0, min(5.0, float(v)))

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    def display_name(self) -> str:
        """Best human-readable name for this lead."""
        return self.studio_name or self.teacher_name or self.website or f"Lead {self.id[:8]}"

    def has_contact(self) -> bool:
        """True if we have at least one way to reach this lead."""
        return bool(self.phone or self.email or self.website)

    def mark_updated(self) -> None:
        """Call this whenever you mutate a lead before saving."""
        self.updated_at = datetime.utcnow()

    def add_source(self, source: SourceType) -> None:
        """Record an additional source sighting without duplicating."""
        if source not in self.sources:
            self.sources.append(source)
        self.mark_updated()

    model_config = {"use_enum_values": True}


# ─────────────────────────────────────────────
# RawLead — unvalidated data from scrapers
# ─────────────────────────────────────────────

class RawLead(BaseModel):
    """
    Loose container for data straight off a scraper before normalization.
    All fields are optional strings so scrapers don't need to pre-clean data.
    The Normalizer converts RawLead → Lead.
    """
    teacher_name: Optional[str]   = None
    studio_name: Optional[str]    = None
    phone: Optional[str]          = None
    email: Optional[str]          = None
    website: Optional[str]        = None
    address: Optional[str]        = None
    zip_code: Optional[str]       = None
    google_place_id: Optional[str] = None
    rating: Optional[str]         = None   # string; normalizer converts to float
    review_count: Optional[str]   = None   # string; normalizer converts to int
    most_recent_review: Optional[str] = None
    photo_count: Optional[str]    = None
    source: str                   = SourceType.MANUAL.value
    territory: str                = Territory.NYC_METRO.value
    raw_data: dict                = Field(
        default_factory=dict,
        description="Full raw payload from the source API/page for debugging.",
    )
