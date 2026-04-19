"""
processors/enricher.py
──────────────────────
Post-storage enrichment. Run after leads are saved to fill in data
that takes extra API calls or time (WHOIS, confidence scoring).

Enrichment is intentionally separate from scraping because:
  - It's slower (external lookups per lead)
  - Some enrichment (WHOIS) has rate limits
  - You can re-run enrichment without re-scraping

Run order:
  scrape → normalize → deduplicate → save → enrich

Usage:
    enricher = Enricher(store)
    enricher.enrich_all()           # enrich every lead missing enrichment
    enricher.enrich_lead(lead_id)   # enrich a single lead
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import whois
from loguru import logger
from tqdm import tqdm

from config.settings import CONFIDENCE_WEIGHTS, NEW_DOMAIN_THRESHOLD_DAYS, REQUEST_DELAY_SECONDS
from storage.schema import Lead
from storage.store import LeadStore
from utils.helpers import extract_domain


class Enricher:
    """
    Enriches stored leads with WHOIS data and confidence scores.
    """

    def __init__(self, store: LeadStore) -> None:
        self._store = store

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def enrich_all(self, force: bool = False) -> int:
        """
        Enrich all leads that haven't been enriched yet.

        Args:
            force: If True, re-enrich even leads that already have a score.

        Returns:
            Number of leads enriched.
        """
        leads = self._store.all_leads()
        to_enrich = leads if force else [l for l in leads if l.confidence_score is None]
        logger.info(f"Enriching {len(to_enrich)} leads...")

        enriched = 0
        for lead in tqdm(to_enrich, desc="Enriching leads", unit="lead"):
            changed = self._enrich(lead)
            if changed:
                self._store.save_lead(lead)
                enriched += 1
            time.sleep(REQUEST_DELAY_SECONDS * 0.5)  # be gentle with WHOIS

        logger.info(f"Enrichment complete: {enriched} leads updated")
        return enriched

    def enrich_lead(self, lead_id: str) -> bool:
        """
        Enrich a single lead by ID.
        Returns True if lead was updated.
        """
        lead = self._store.get_lead(lead_id)
        if not lead:
            logger.warning(f"enrich_lead: {lead_id} not found")
            return False
        changed = self._enrich(lead)
        if changed:
            self._store.save_lead(lead)
        return changed

    # ─────────────────────────────────────────
    # Enrichment logic
    # ─────────────────────────────────────────

    def _enrich(self, lead: Lead) -> bool:
        """
        Apply all enrichment to a lead in-place.
        Returns True if any field was changed.
        """
        changed = False

        # WHOIS lookup (only if website is present and domain_age not yet set)
        if lead.website and lead.domain_age_days is None:
            domain_data = self._lookup_whois(lead.website)
            if domain_data:
                created, age_days = domain_data
                lead.domain_created = created
                lead.domain_age_days = age_days
                changed = True

                if age_days <= NEW_DOMAIN_THRESHOLD_DAYS:
                    logger.debug(
                        f"New domain ({age_days}d old): {extract_domain(lead.website)}"
                    )

        # Always recalculate confidence score
        new_score = self._calculate_confidence(lead)
        if new_score != lead.confidence_score:
            lead.confidence_score = new_score
            changed = True

        return changed

    # ─────────────────────────────────────────
    # WHOIS
    # ─────────────────────────────────────────

    def _lookup_whois(
        self,
        website: str,
    ) -> Optional[tuple[datetime, int]]:
        """
        Look up WHOIS for a domain.
        Returns (creation_date, age_in_days) or None on failure.
        """
        domain = extract_domain(website)
        if not domain:
            return None

        try:
            w = whois.whois(domain)
            creation_date = w.creation_date

            # whois returns either a datetime or a list of datetimes
            if isinstance(creation_date, list):
                creation_date = creation_date[0]

            if not isinstance(creation_date, datetime):
                return None

            age_days = (datetime.utcnow() - creation_date).days
            logger.debug(f"WHOIS {domain}: created={creation_date.date()}, age={age_days}d")
            return creation_date, age_days

        except Exception as e:
            logger.debug(f"WHOIS failed for {domain}: {e}")
            return None

    # ─────────────────────────────────────────
    # Confidence scoring
    # ─────────────────────────────────────────

    def _calculate_confidence(self, lead: Lead) -> int:
        """
        Calculate a 1–10 confidence score based on data completeness.

        Scoring uses weights from config/settings.py:
          has_phone:           2 pts  (phone = directly reachable)
          has_website:         1 pt
          has_email:           1 pt
          has_rating:          1 pt   (Google Maps verified)
          review_count_10plus: 1 pt   (established, active)
          review_count_50plus: 1 pt   (well-established, stacks)
          multiple_sources:    2 pts  (seen in 2+ sources = stronger signal)
          has_photo:           1 pt   (professional presence)

        Max = 10.
        """
        w = CONFIDENCE_WEIGHTS
        score = 0

        if lead.phone:
            score += w.get("has_phone", 0)
        if lead.website:
            score += w.get("has_website", 0)
        if lead.email:
            score += w.get("has_email", 0)
        if lead.rating:
            score += w.get("has_rating", 0)
        if lead.review_count and lead.review_count >= 10:
            score += w.get("review_count_10plus", 0)
        if lead.review_count and lead.review_count >= 50:
            score += w.get("review_count_50plus", 0)
        if len(lead.sources) >= 2:
            score += w.get("multiple_sources", 0)
        if lead.photo_count and lead.photo_count > 0:
            score += w.get("has_photo", 0)

        # Clamp to 1–10
        return max(1, min(10, score))
