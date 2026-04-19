"""
processors/deduplicator.py
──────────────────────────
Detects duplicate leads and either merges them automatically or flags them
for human review.

Duplicate detection strategy (in priority order):
  1. Google Place ID match     → same business, auto-merge
  2. Phone number match        → very likely same, auto-merge
  3. Domain match              → same website, auto-merge
  4. Fuzzy name match          → possible duplicate, flag for review

"Auto-merge" means: the newer lead's data is folded into the existing lead
(filling in any missing fields), and the sources list is updated.
The newer lead is NOT stored as a separate record.

"Flag for review" means: both leads are stored, but the newer one gets a
`duplicate_of` field set to the candidate's ID, and a note is added.
The rep can then confirm or dismiss the duplicate via the CLI.

Design rules:
  - Never silently delete a lead. Mark as duplicate, not deleted.
  - Prefer the record with more data (more fields filled in).
  - Always preserve the original found_at timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from storage.schema import Lead, SourceType
from storage.store import LeadStore
from utils.helpers import extract_domain


@dataclass
class DuplicateMatch:
    """Result of a duplicate check."""
    existing_lead: Lead
    match_reason: str          # "place_id", "phone", "domain", "name"
    confidence: str            # "high" (auto-merge) or "low" (needs review)
    auto_merge: bool


class Deduplicator:
    """
    Checks incoming leads against the store for duplicates.

    Usage:
        deduper = Deduplicator(store)
        result = deduper.check(new_lead)
        if result:
            if result.auto_merge:
                merged = deduper.merge(result.existing_lead, new_lead)
                store.save_lead(merged)
            else:
                # flag for human review
                new_lead.duplicate_of = result.existing_lead.id
                store.save_lead(new_lead)
        else:
            store.save_lead(new_lead)  # genuinely new
    """

    # How similar names must be (0.0–1.0) to flag as possible duplicate
    NAME_SIMILARITY_THRESHOLD = 0.82

    def __init__(self, store: LeadStore) -> None:
        self._store = store

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def check(self, lead: Lead) -> Optional[DuplicateMatch]:
        """
        Check a lead against all existing leads for duplicates.
        Returns the best match found, or None if genuinely new.
        Checks in priority order: place_id → phone → domain → name.
        """
        # 1. Google Place ID — strongest signal
        if lead.google_place_id:
            match = self._check_place_id(lead)
            if match:
                return match

        # 2. Phone number — very reliable
        if lead.phone:
            match = self._check_phone(lead)
            if match:
                return match

        # 3. Domain — reliable for website-based leads
        if lead.website:
            match = self._check_domain(lead)
            if match:
                return match

        # 4. Name similarity — fuzzy, flag for human review only
        match = self._check_name(lead)
        if match:
            return match

        return None

    def process(self, lead: Lead) -> tuple[Lead, bool]:
        """
        Full deduplication pipeline for a single lead.

        Returns:
            (lead_to_save, is_new):
              - is_new=True  → save as new record
              - is_new=False → existing record was updated (or lead flagged)

        The returned lead is always the one that should be saved.
        """
        match = self.check(lead)

        if not match:
            return lead, True  # genuinely new

        existing = match.existing_lead

        if match.auto_merge:
            # Merge new data into existing record
            merged = self.merge(existing, lead)
            logger.info(
                f"Auto-merged duplicate | reason={match.match_reason} | "
                f"'{lead.display_name()}' → '{existing.display_name()}'"
            )
            return merged, False
        else:
            # Flag for human review — store both, link them
            lead.duplicate_of = existing.id
            lead.notes = (
                f"[AUTO-FLAGGED] Possible duplicate of {existing.id[:8]} "
                f"({existing.display_name()}) — reason: {match.match_reason}. "
                "Please review and merge or dismiss."
            )
            logger.info(
                f"Flagged for review | reason={match.match_reason} | "
                f"'{lead.display_name()}' may duplicate '{existing.display_name()}'"
            )
            return lead, True  # store as separate record with flag

    def merge(self, primary: Lead, secondary: Lead) -> Lead:
        """
        Merge secondary into primary, filling gaps without overwriting good data.

        Rules:
          - primary's ID and found_at are always preserved
          - For each field: keep primary's value if set, else use secondary's
          - sources list gets both sources merged
          - confidence_score is recalculated
        """
        # Fields that can be filled in from secondary if primary has None
        fillable_fields = [
            "teacher_name", "studio_name", "phone", "email", "website",
            "address", "zip_code", "google_place_id", "rating",
            "review_count", "most_recent_review", "photo_count",
            "domain_created", "domain_age_days",
        ]

        for field in fillable_fields:
            if getattr(primary, field) is None:
                secondary_val = getattr(secondary, field, None)
                if secondary_val is not None:
                    setattr(primary, field, secondary_val)

        # Merge sources lists
        for source in secondary.sources:
            primary.add_source(source)
        if secondary.source not in primary.sources:
            primary.add_source(secondary.source)

        # Prefer better review data (higher count = more current)
        if secondary.review_count and primary.review_count:
            if secondary.review_count > primary.review_count:
                primary.review_count = secondary.review_count
                primary.rating = secondary.rating

        primary.mark_updated()
        return primary

    def get_pending_reviews(self) -> list[tuple[Lead, Optional[Lead]]]:
        """
        Return all leads flagged as possible duplicates, paired with their
        candidate match. For use in the CLI review workflow.

        Returns list of (flagged_lead, candidate_lead) tuples.
        """
        flagged = [l for l in self._store.all_leads() if l.duplicate_of]
        pairs = []
        for lead in flagged:
            candidate = self._store.get_lead(lead.duplicate_of)
            pairs.append((lead, candidate))
        return pairs

    def dismiss_duplicate_flag(self, lead_id: str) -> bool:
        """
        Mark a flagged lead as NOT a duplicate (rep reviewed and dismissed).
        Clears the duplicate_of field and removes the auto-flag note.
        """
        lead = self._store.get_lead(lead_id)
        if not lead:
            return False
        lead.duplicate_of = None
        if lead.notes and "[AUTO-FLAGGED]" in lead.notes:
            lead.notes = lead.notes.split("[AUTO-FLAGGED]")[0].strip() or None
        self._store.save_lead(lead)
        logger.info(f"Dismissed duplicate flag for {lead_id[:8]}")
        return True

    # ─────────────────────────────────────────
    # Match checkers
    # ─────────────────────────────────────────

    def _check_place_id(self, lead: Lead) -> Optional[DuplicateMatch]:
        existing = next(
            (l for l in self._store.all_leads()
             if l.google_place_id and l.google_place_id == lead.google_place_id),
            None,
        )
        if existing and existing.id != lead.id:
            return DuplicateMatch(
                existing_lead=existing,
                match_reason="place_id",
                confidence="high",
                auto_merge=True,
            )
        return None

    def _check_phone(self, lead: Lead) -> Optional[DuplicateMatch]:
        matches = self._store.find_by_phone(lead.phone)
        matches = [m for m in matches if m.id != lead.id]
        if matches:
            return DuplicateMatch(
                existing_lead=matches[0],
                match_reason="phone",
                confidence="high",
                auto_merge=True,
            )
        return None

    def _check_domain(self, lead: Lead) -> Optional[DuplicateMatch]:
        domain = extract_domain(lead.website)
        if not domain:
            return None
        matches = self._store.find_by_domain(domain)
        matches = [m for m in matches if m.id != lead.id]
        if matches:
            return DuplicateMatch(
                existing_lead=matches[0],
                match_reason="domain",
                confidence="high",
                auto_merge=True,
            )
        return None

    def _check_name(self, lead: Lead) -> Optional[DuplicateMatch]:
        """
        Fuzzy name match. Only flags — never auto-merges.
        Uses a simple character-level similarity ratio.
        """
        lead_name = _best_name(lead)
        if not lead_name or len(lead_name) < 4:
            return None

        best_score = 0.0
        best_match = None

        for existing in self._store.all_leads():
            if existing.id == lead.id:
                continue
            existing_name = _best_name(existing)
            if not existing_name:
                continue
            score = _name_similarity(lead_name, existing_name)
            if score > best_score:
                best_score = score
                best_match = existing

        if best_match and best_score >= self.NAME_SIMILARITY_THRESHOLD:
            return DuplicateMatch(
                existing_lead=best_match,
                match_reason=f"name (similarity={best_score:.0%})",
                confidence="low",
                auto_merge=False,
            )
        return None


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _best_name(lead: Lead) -> str:
    """Return the best available name string for comparison."""
    return (lead.studio_name or lead.teacher_name or "").lower().strip()


def _name_similarity(a: str, b: str) -> float:
    """
    Simple Jaccard similarity on character bigrams.
    Fast, no dependencies, good enough for name deduplication.
    """
    def bigrams(s: str) -> set[str]:
        s = s.lower().strip()
        return {s[i:i+2] for i in range(len(s) - 1)} if len(s) > 1 else set()

    set_a = bigrams(a)
    set_b = bigrams(b)
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)
