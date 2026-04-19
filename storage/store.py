"""
storage/store.py
────────────────
JSON-backed lead store. Handles all read/write operations.

Design rules:
  - The JSON file is the database. No external dependencies.
  - Reads always return Lead objects (never raw dicts).
  - Writes always go through save_lead() so updated_at stays current.
  - Atomic writes: write to a temp file then rename, so a crash mid-write
    never corrupts the database.
  - Thread-safe: uses a file lock for concurrent scraper runs.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from loguru import logger

from storage.schema import Lead, LeadStatus, SourceType, Territory


# ─────────────────────────────────────────────
# LeadStore
# ─────────────────────────────────────────────

class LeadStore:
    """
    Manages the leads JSON file.

    Usage:
        store = LeadStore("output/leads.json")
        store.save_lead(lead)
        leads = store.all_leads()
        store.mark_taken(lead_id, assigned_to="Sarah")
    """

    def __init__(self, db_path: str | Path = "output/leads.json") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    # ─────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────

    def _ensure_file(self) -> None:
        """Create (or reinitialize) the JSON file if missing or empty."""
        needs_init = (
            not self.db_path.exists()
            or self.db_path.stat().st_size == 0
        )
        if needs_init:
            self._write_raw({"leads": [], "meta": {"created_at": _now_iso(), "version": "1"}})
            logger.info(f"Created new leads database at {self.db_path}")

    def _read_raw(self) -> dict:
        """Load raw JSON from disk."""
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read leads file: {e}")
            raise

    def _write_raw(self, data: dict) -> None:
        """
        Atomically write data to the JSON file.
        Writes to a temp file first, then renames — safe against crashes.
        """
        tmp_path = self.db_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=_json_serializer, ensure_ascii=False)
            tmp_path.rename(self.db_path)
        except OSError as e:
            logger.error(f"Failed to write leads file: {e}")
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def _load_leads(self) -> dict[str, Lead]:
        """Return all leads keyed by ID."""
        raw = self._read_raw()
        leads: dict[str, Lead] = {}
        for item in raw.get("leads", []):
            try:
                lead = Lead.model_validate(item)
                leads[lead.id] = lead
            except Exception as e:
                logger.warning(f"Skipping malformed lead record: {e} | data={item}")
        return leads

    def _save_all(self, leads: dict[str, Lead]) -> None:
        """Serialize and write all leads to disk."""
        raw = self._read_raw()
        raw["leads"] = [lead.model_dump(mode="json") for lead in leads.values()]
        raw["meta"]["updated_at"] = _now_iso()
        raw["meta"]["count"] = len(leads)
        self._write_raw(raw)

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def all_leads(self) -> list[Lead]:
        """Return all leads, newest first."""
        leads = self._load_leads()
        return sorted(leads.values(), key=lambda l: l.found_at, reverse=True)

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Fetch a single lead by ID. Returns None if not found."""
        leads = self._load_leads()
        return leads.get(lead_id)

    def save_lead(self, lead: Lead) -> bool:
        """
        Insert or update a lead.
        Returns True if inserted as new, False if updated existing.
        """
        leads = self._load_leads()
        is_new = lead.id not in leads
        lead.mark_updated()
        leads[lead.id] = lead
        self._save_all(leads)
        action = "Saved new" if is_new else "Updated"
        logger.debug(f"{action} lead: {lead.id[:8]} | {lead.display_name()}")
        return is_new

    def save_leads(self, new_leads: list[Lead]) -> tuple[int, int]:
        """
        Bulk insert/update. Returns (inserted_count, updated_count).
        More efficient than calling save_lead() in a loop.
        """
        leads = self._load_leads()
        inserted = 0
        updated = 0
        for lead in new_leads:
            is_new = lead.id not in leads
            lead.mark_updated()
            leads[lead.id] = lead
            if is_new:
                inserted += 1
            else:
                updated += 1
        self._save_all(leads)
        logger.info(f"Bulk save: {inserted} new, {updated} updated")
        return inserted, updated

    def mark_taken(self, lead_id: str, assigned_to: Optional[str] = None) -> bool:
        """Mark a lead as taken (claimed by a rep). Returns False if not found."""
        lead = self.get_lead(lead_id)
        if not lead:
            logger.warning(f"mark_taken: lead {lead_id} not found")
            return False
        lead.status = LeadStatus.TAKEN
        if assigned_to:
            lead.assigned_to = assigned_to
        self.save_lead(lead)
        logger.info(f"Lead {lead_id[:8]} marked taken" + (f" by {assigned_to}" if assigned_to else ""))
        return True

    def update_status(self, lead_id: str, status: LeadStatus) -> bool:
        """Update lead status. Returns False if not found."""
        lead = self.get_lead(lead_id)
        if not lead:
            return False
        lead.status = status
        self.save_lead(lead)
        return True

    def find_by_phone(self, phone: str) -> list[Lead]:
        """Return all leads matching this normalized phone number."""
        digits = "".join(c for c in phone if c.isdigit())
        return [l for l in self.all_leads() if l.phone == digits]

    def find_by_domain(self, domain: str) -> list[Lead]:
        """Return all leads whose website contains this domain."""
        domain = domain.lower().strip()
        return [
            l for l in self.all_leads()
            if l.website and domain in l.website.lower()
        ]

    def filter(
        self,
        territory: Optional[Territory] = None,
        source: Optional[SourceType] = None,
        status: Optional[LeadStatus] = None,
        has_phone: Optional[bool] = None,
        has_website: Optional[bool] = None,
        min_rating: Optional[float] = None,
        min_reviews: Optional[int] = None,
        sort_by: str = "found_at",
        sort_desc: bool = True,
    ) -> list[Lead]:
        """
        Filter and sort leads.

        sort_by options: found_at, rating, review_count, most_recent_review,
                         photo_count, domain_age_days, confidence_score
        """
        leads = self.all_leads()

        if territory:
            leads = [l for l in leads if l.territory == territory]
        if source:
            leads = [l for l in leads if l.source == source or source in l.sources]
        if status:
            leads = [l for l in leads if l.status == status]
        if has_phone is not None:
            leads = [l for l in leads if bool(l.phone) == has_phone]
        if has_website is not None:
            leads = [l for l in leads if bool(l.website) == has_website]
        if min_rating is not None:
            leads = [l for l in leads if l.rating and l.rating >= min_rating]
        if min_reviews is not None:
            leads = [l for l in leads if l.review_count and l.review_count >= min_reviews]

        # Sort — handle None values by putting them last
        def sort_key(l: Lead):
            val = getattr(l, sort_by, None)
            if val is None:
                return (1, 0)  # (has_none=1, value) — sorts after real values
            return (0, val if not isinstance(val, datetime) else val.timestamp())

        leads.sort(key=sort_key, reverse=sort_desc)
        return leads

    def stats(self) -> dict:
        """Summary statistics about the lead database."""
        leads = self.all_leads()
        total = len(leads)
        if not total:
            return {"total": 0}

        by_status   = _count_by(leads, lambda l: l.status.value)
        by_territory = _count_by(leads, lambda l: l.territory.value)
        by_source   = _count_by(leads, lambda l: l.source.value)

        return {
            "total": total,
            "by_status": by_status,
            "by_territory": by_territory,
            "by_source": by_source,
            "with_phone": sum(1 for l in leads if l.phone),
            "with_website": sum(1 for l in leads if l.website),
            "with_email": sum(1 for l in leads if l.email),
            "new_leads": by_status.get("new", 0),
        }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _json_serializer(obj):
    """Handle datetime and Enum serialization for json.dump."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _count_by(leads: list[Lead], key_fn: Callable) -> dict[str, int]:
    counts: dict[str, int] = {}
    for lead in leads:
        k = key_fn(lead)
        counts[k] = counts.get(k, 0) + 1
    return counts
