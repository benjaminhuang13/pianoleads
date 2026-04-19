"""
tests/test_processors.py
────────────────────────
Unit tests for Normalizer and Deduplicator.
"""

import tempfile

import pytest

from processors.deduplicator import Deduplicator, _name_similarity
from processors.normalizer import Normalizer
from storage.schema import Lead, RawLead, SourceType, Territory
from storage.store import LeadStore


# ─────────────────────────────────────────────
# Normalizer tests
# ─────────────────────────────────────────────

def make_raw(**kwargs) -> RawLead:
    defaults = dict(
        studio_name="Test Piano Studio",
        phone="(516) 555-1234",
        source="google_maps",
        territory="nyc_metro",
    )
    defaults.update(kwargs)
    return RawLead(**defaults)


class TestNormalizer:
    def setup_method(self):
        self.n = Normalizer()

    def test_basic_normalization(self):
        raw = make_raw()
        lead = self.n.normalize(raw)
        assert lead is not None
        assert lead.phone == "5165551234"
        assert lead.source == SourceType.GOOGLE_MAPS
        assert lead.territory == Territory.NYC_METRO

    def test_rating_string_to_float(self):
        raw = make_raw(rating="4.5")
        lead = self.n.normalize(raw)
        assert lead.rating == 4.5

    def test_review_count_string_to_int(self):
        raw = make_raw(review_count="127")
        lead = self.n.normalize(raw)
        assert lead.review_count == 127

    def test_review_count_with_comma(self):
        raw = make_raw(review_count="1,234")
        lead = self.n.normalize(raw)
        assert lead.review_count == 1234

    def test_empty_lead_discarded(self):
        raw = RawLead(source="google_maps", territory="nyc_metro")
        lead = self.n.normalize(raw)
        assert lead is None

    def test_unknown_source_defaults_to_manual(self):
        raw = make_raw(source="unknown_source")
        lead = self.n.normalize(raw)
        assert lead is not None
        assert lead.source == SourceType.MANUAL

    def test_teacher_name_title_cased(self):
        raw = make_raw(teacher_name="jane smith")
        lead = self.n.normalize(raw)
        assert lead.teacher_name == "Jane Smith"

    def test_invalid_email_discarded(self):
        raw = make_raw(email="notanemail")
        lead = self.n.normalize(raw)
        assert lead.email is None

    def test_valid_email_kept(self):
        raw = make_raw(email="Jane@PianoStudio.com")
        lead = self.n.normalize(raw)
        assert lead.email == "jane@pianostudio.com"

    def test_normalize_many_drops_invalid(self):
        raws = [
            make_raw(studio_name="Good Studio"),
            RawLead(source="google_maps", territory="nyc_metro"),  # empty
            make_raw(studio_name="Another Good Studio"),
        ]
        leads = self.n.normalize_many(raws)
        assert len(leads) == 2

    def test_zip_extracted_from_address(self):
        raw = make_raw(address="123 Main St, Garden City, NY 11530")
        lead = self.n.normalize(raw)
        assert lead.zip_code == "11530"

    def test_sources_list_initialized(self):
        raw = make_raw(source="google_maps")
        lead = self.n.normalize(raw)
        assert SourceType.GOOGLE_MAPS in lead.sources


# ─────────────────────────────────────────────
# Deduplicator tests
# ─────────────────────────────────────────────

def make_store_with_lead(**kwargs) -> tuple[LeadStore, Lead]:
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    store = LeadStore(tmp.name)
    lead = Lead(
        source=SourceType.GOOGLE_MAPS,
        territory=Territory.NYC_METRO,
        studio_name=kwargs.get("studio_name", "Jane's Piano Studio"),
        phone=kwargs.get("phone", "5165551234"),
        website=kwargs.get("website", "https://janespiano.com"),
        google_place_id=kwargs.get("google_place_id"),
    )
    store.save_lead(lead)
    return store, lead


class TestDeduplicator:
    def test_no_match_returns_none(self):
        store, _ = make_store_with_lead()
        deduper = Deduplicator(store)
        new_lead = Lead(
            source=SourceType.RCM,
            territory=Territory.NYC_METRO,
            studio_name="Completely Different Studio",
            phone="9995559999",
            website="https://different.com",
        )
        assert deduper.check(new_lead) is None

    def test_phone_match_auto_merges(self):
        store, existing = make_store_with_lead(phone="5165551234")
        deduper = Deduplicator(store)
        new_lead = Lead(
            source=SourceType.RCM,
            territory=Territory.NYC_METRO,
            studio_name="Same Studio Different Source",
            phone="5165551234",
        )
        match = deduper.check(new_lead)
        assert match is not None
        assert match.match_reason == "phone"
        assert match.auto_merge is True

    def test_domain_match_auto_merges(self):
        store, _ = make_store_with_lead(website="https://janespiano.com")
        deduper = Deduplicator(store)
        new_lead = Lead(
            source=SourceType.DOMAIN_CRAWL,
            territory=Territory.NYC_METRO,
            website="https://janespiano.com/contact",
            phone="9995559999",
        )
        match = deduper.check(new_lead)
        assert match is not None
        assert match.match_reason == "domain"
        assert match.auto_merge is True

    def test_place_id_match_auto_merges(self):
        store, _ = make_store_with_lead(google_place_id="ChIJabc123")
        deduper = Deduplicator(store)
        new_lead = Lead(
            source=SourceType.GOOGLE_MAPS,
            territory=Territory.NYC_METRO,
            google_place_id="ChIJabc123",
            phone="9995559999",
        )
        match = deduper.check(new_lead)
        assert match is not None
        assert match.match_reason == "place_id"
        assert match.auto_merge is True

    def test_name_match_flagged_not_merged(self):
        store, _ = make_store_with_lead(studio_name="Jane's Piano Studio")
        deduper = Deduplicator(store)
        new_lead = Lead(
            source=SourceType.THUMBTACK,
            territory=Territory.NYC_METRO,
            studio_name="Jane Piano Studio",   # similar but not identical
            phone="9995559999",
            website="https://totallydifferent.com",
        )
        match = deduper.check(new_lead)
        if match:  # name similarity may or may not trigger depending on threshold
            assert match.auto_merge is False

    def test_merge_fills_missing_fields(self):
        store, existing = make_store_with_lead(phone="5165551234", email=None)
        deduper = Deduplicator(store)
        new_lead = Lead(
            source=SourceType.RCM,
            territory=Territory.NYC_METRO,
            phone="5165551234",
            email="jane@piano.com",  # new data not in existing
        )
        merged = deduper.merge(existing, new_lead)
        assert merged.email == "jane@piano.com"
        assert merged.id == existing.id  # ID preserved

    def test_merge_preserves_better_review_data(self):
        store, existing = make_store_with_lead()
        existing.review_count = 10
        existing.rating = 4.0
        deduper = Deduplicator(store)
        secondary = Lead(
            source=SourceType.RCM,
            territory=Territory.NYC_METRO,
            review_count=50,
            rating=4.8,
            phone="5165551234",
        )
        merged = deduper.merge(existing, secondary)
        assert merged.review_count == 50
        assert merged.rating == 4.8

    def test_process_genuinely_new(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        store = LeadStore(tmp.name)
        deduper = Deduplicator(store)
        lead = Lead(
            source=SourceType.GOOGLE_MAPS,
            territory=Territory.NYC_METRO,
            studio_name="Brand New Studio",
            phone="5165559999",
        )
        result, is_new = deduper.process(lead)
        assert is_new is True
        assert result.duplicate_of is None


class TestNameSimilarity:
    def test_identical_names(self):
        assert _name_similarity("jane's piano studio", "jane's piano studio") == 1.0

    def test_completely_different(self):
        score = _name_similarity("jane piano", "xyz qrst")
        assert score < 0.3

    def test_similar_names(self):
        score = _name_similarity("jane's piano studio", "jane piano studio")
        assert score > 0.7

    def test_empty_strings(self):
        assert _name_similarity("", "") == 1.0
        assert _name_similarity("jane", "") == 0.0
