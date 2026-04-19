"""
tests/test_store.py
───────────────────
Unit tests for LeadStore — save, retrieve, filter, mark, stats.
Uses a temp file so no test data touches the real database.
"""

import tempfile
from pathlib import Path

import pytest

from storage.schema import Lead, LeadStatus, SourceType, Territory
from storage.store import LeadStore


def make_store() -> tuple[LeadStore, Path]:
    """Create a LeadStore backed by a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    store = LeadStore(tmp.name)
    return store, Path(tmp.name)


def make_lead(
    studio_name="Test Piano Studio",
    phone="5165551234",
    source=SourceType.GOOGLE_MAPS,
    territory=Territory.NYC_METRO,
    **kwargs,
) -> Lead:
    return Lead(source=source, territory=territory, studio_name=studio_name, phone=phone, **kwargs)


class TestSaveAndRetrieve:
    def test_save_and_get(self):
        store, _ = make_store()
        lead = make_lead()
        store.save_lead(lead)
        retrieved = store.get_lead(lead.id)
        assert retrieved is not None
        assert retrieved.id == lead.id
        assert retrieved.studio_name == "Test Piano Studio"

    def test_get_nonexistent_returns_none(self):
        store, _ = make_store()
        assert store.get_lead("nonexistent-id") is None

    def test_save_updates_existing(self):
        store, _ = make_store()
        lead = make_lead()
        store.save_lead(lead)
        lead.studio_name = "Updated Name"
        store.save_lead(lead)
        retrieved = store.get_lead(lead.id)
        assert retrieved.studio_name == "Updated Name"

    def test_all_leads_returns_all(self):
        store, _ = make_store()
        leads = [make_lead(studio_name=f"Studio {i}", phone=f"516555{i:04d}") for i in range(5)]
        for lead in leads:
            store.save_lead(lead)
        all_leads = store.all_leads()
        assert len(all_leads) == 5

    def test_bulk_save(self):
        store, _ = make_store()
        leads = [make_lead(studio_name=f"Studio {i}", phone=f"516555{i:04d}") for i in range(10)]
        inserted, updated = store.save_leads(leads)
        assert inserted == 10
        assert updated == 0


class TestLookups:
    def test_find_by_phone(self):
        store, _ = make_store()
        lead = make_lead(phone="5165551234")
        store.save_lead(lead)
        results = store.find_by_phone("(516) 555-1234")
        assert len(results) == 1
        assert results[0].id == lead.id

    def test_find_by_phone_no_match(self):
        store, _ = make_store()
        store.save_lead(make_lead(phone="5165551234"))
        assert store.find_by_phone("9995559999") == []

    def test_find_by_domain(self):
        store, _ = make_store()
        lead = make_lead(website="https://janespiano.com/lessons")
        store.save_lead(lead)
        results = store.find_by_domain("janespiano.com")
        assert len(results) == 1

    def test_find_by_domain_no_match(self):
        store, _ = make_store()
        store.save_lead(make_lead(website="https://janespiano.com"))
        assert store.find_by_domain("otherpiano.com") == []


class TestStatusManagement:
    def test_mark_taken(self):
        store, _ = make_store()
        lead = make_lead()
        store.save_lead(lead)
        result = store.mark_taken(lead.id, assigned_to="Sarah")
        assert result is True
        updated = store.get_lead(lead.id)
        assert updated.status == LeadStatus.TAKEN
        assert updated.assigned_to == "Sarah"

    def test_mark_taken_nonexistent(self):
        store, _ = make_store()
        assert store.mark_taken("bad-id") is False

    def test_update_status(self):
        store, _ = make_store()
        lead = make_lead()
        store.save_lead(lead)
        store.update_status(lead.id, LeadStatus.CONTACTED)
        updated = store.get_lead(lead.id)
        assert updated.status == LeadStatus.CONTACTED


class TestFilter:
    def setup_method(self):
        self.store, _ = make_store()
        self.store.save_lead(make_lead(
            studio_name="NYC Studio", phone="2125551111",
            territory=Territory.NYC_METRO, rating=4.5, review_count=20
        ))
        self.store.save_lead(make_lead(
            studio_name="LI Studio", phone="5165552222",
            territory=Territory.LONG_ISLAND, rating=3.0, review_count=5
        ))
        self.store.save_lead(make_lead(
            studio_name="NJ Studio", phone="2015553333",
            territory=Territory.NORTH_JERSEY, rating=4.8, review_count=100,
            source=SourceType.RCM
        ))

    def test_filter_by_territory(self):
        results = self.store.filter(territory=Territory.LONG_ISLAND)
        assert len(results) == 1
        assert results[0].studio_name == "LI Studio"

    def test_filter_by_source(self):
        results = self.store.filter(source=SourceType.RCM)
        assert len(results) == 1
        assert results[0].studio_name == "NJ Studio"

    def test_filter_min_rating(self):
        results = self.store.filter(min_rating=4.0)
        assert len(results) == 2

    def test_filter_min_reviews(self):
        results = self.store.filter(min_reviews=50)
        assert len(results) == 1
        assert results[0].studio_name == "NJ Studio"

    def test_filter_has_phone(self):
        results = self.store.filter(has_phone=True)
        assert len(results) == 3


class TestStats:
    def test_empty_stats(self):
        store, _ = make_store()
        stats = store.stats()
        assert stats["total"] == 0

    def test_stats_counts(self):
        store, _ = make_store()
        store.save_lead(make_lead(studio_name="A", phone="5165551111"))
        store.save_lead(make_lead(studio_name="B", phone="5165552222"))
        stats = store.stats()
        assert stats["total"] == 2
        assert stats["with_phone"] == 2
        assert stats["new_leads"] == 2
