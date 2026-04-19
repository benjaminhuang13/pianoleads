"""
processors/normalizer.py
────────────────────────
Converts RawLead → Lead (validated, typed, clean).

This is the transformation layer between what scrapers return and what
gets stored. It handles:
  - Type conversion (strings → int/float/datetime)
  - Field cleaning (whitespace, casing)
  - Defaults for missing data
  - Graceful handling of malformed values

Design rule: never raise on bad data — log a warning and use None instead.
The goal is to always produce a Lead, even from messy scraped data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from loguru import logger

from storage.schema import Lead, RawLead, SourceType, Territory
from utils.helpers import clean_text, extract_zip_from_address, title_case_name


class Normalizer:
    """
    Converts RawLead objects into validated Lead objects.

    Usage:
        normalizer = Normalizer()
        lead = normalizer.normalize(raw_lead)
        leads = normalizer.normalize_many(raw_leads)
    """

    def normalize(self, raw: RawLead) -> Optional[Lead]:
        """
        Convert a single RawLead to a Lead.
        Returns None if the raw lead is too empty to be useful.
        """
        try:
            lead = Lead(
                teacher_name=title_case_name(raw.teacher_name),
                studio_name=clean_text(raw.studio_name),
                phone=raw.phone,           # Lead validator handles normalization
                email=self._clean_email(raw.email),
                website=raw.website,       # Lead validator adds scheme
                address=clean_text(raw.address),
                zip_code=self._resolve_zip(raw),
                google_place_id=raw.google_place_id,
                rating=self._parse_float(raw.rating, "rating"),
                review_count=self._parse_int(raw.review_count, "review_count"),
                most_recent_review=self._parse_datetime(raw.most_recent_review, "most_recent_review"),
                photo_count=self._parse_int(raw.photo_count, "photo_count"),
                source=self._parse_source(raw.source),
                territory=self._parse_territory(raw.territory),
                sources=[self._parse_source(raw.source)],  # initialize sources list
            )
        except Exception as e:
            logger.warning(f"Normalizer failed for raw lead '{raw.studio_name or raw.teacher_name}': {e}")
            return None

        # Reject leads with nothing useful
        if not self._has_minimum_data(lead):
            logger.debug(f"Discarding lead with insufficient data: {lead.display_name()}")
            return None

        return lead

    def normalize_many(self, raws: list[RawLead]) -> list[Lead]:
        """Normalize a list of RawLeads, silently dropping failures."""
        leads = []
        skipped = 0
        for raw in raws:
            lead = self.normalize(raw)
            if lead:
                leads.append(lead)
            else:
                skipped += 1
        if skipped:
            logger.debug(f"Normalizer: {len(leads)} leads kept, {skipped} discarded")
        return leads

    # ─────────────────────────────────────────
    # Field parsers — all return None on failure
    # ─────────────────────────────────────────

    def _parse_float(self, value: Optional[str], field: str) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.debug(f"Could not parse {field}='{value}' as float")
            return None

    def _parse_int(self, value: Optional[str], field: str) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            # Handle strings like "1,234" from some sources
            return int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            logger.debug(f"Could not parse {field}='{value}' as int")
            return None

    def _parse_datetime(self, value: Optional[str], field: str) -> Optional[datetime]:
        if value is None or value == "":
            return None
        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%B %d, %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value.split("+")[0].split("Z")[0], fmt)
            except ValueError:
                continue
        logger.debug(f"Could not parse {field}='{value}' as datetime")
        return None

    def _parse_source(self, value: str) -> SourceType:
        try:
            return SourceType(value)
        except ValueError:
            logger.warning(f"Unknown source '{value}', defaulting to MANUAL")
            return SourceType.MANUAL

    def _parse_territory(self, value: str) -> Territory:
        try:
            return Territory(value)
        except ValueError:
            logger.warning(f"Unknown territory '{value}', defaulting to NYC_METRO")
            return Territory.NYC_METRO

    def _clean_email(self, email: Optional[str]) -> Optional[str]:
        if not email:
            return None
        email = email.strip().lower()
        # Basic sanity check
        if "@" not in email or "." not in email.split("@")[-1]:
            return None
        return email

    def _resolve_zip(self, raw: RawLead) -> Optional[str]:
        """Use raw.zip_code if present, otherwise try to extract from address."""
        if raw.zip_code:
            return raw.zip_code.strip()
        if raw.address:
            return extract_zip_from_address(raw.address)
        return None

    def _has_minimum_data(self, lead: Lead) -> bool:
        """
        A lead must have at least a name (teacher or studio) OR a website
        to be worth keeping. A phone with no name is borderline but keep it.
        """
        has_name = bool(lead.teacher_name or lead.studio_name)
        has_contact = bool(lead.phone or lead.email or lead.website)
        return has_name or has_contact
