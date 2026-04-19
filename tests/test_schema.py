"""
tests/test_schema.py
────────────────────
Unit tests for the Lead schema — validators, helpers, enum behavior.
"""

import pytest
from storage.schema import Lead, RawLead, LeadStatus, SourceType, Territory


def make_lead(**kwargs) -> Lead:
    defaults = dict(source=SourceType.GOOGLE_MAPS, territory=Territory.NYC_METRO)
    defaults.update(kwargs)
    return Lead(**defaults)


class TestPhoneNormalization:
    def test_strips_formatting(self):
        lead = make_lead(phone="(516) 555-1234")
        assert lead.phone == "5165551234"

    def test_strips_country_code(self):
        lead = make_lead(phone="+1 516 555 1234")
        assert lead.phone == "5165551234"

    def test_none_stays_none(self):
        lead = make_lead(phone=None)
        assert lead.phone is None

    def test_invalid_phone_becomes_none(self):
        lead = make_lead(phone="123")
        assert lead.phone is None

    def test_dots_as_separator(self):
        lead = make_lead(phone="516.555.1234")
        assert lead.phone == "5165551234"


class TestWebsiteNormalization:
    def test_adds_https_scheme(self):
        lead = make_lead(website="janespiano.com")
        assert lead.website == "https://janespiano.com"

    def test_preserves_existing_scheme(self):
        lead = make_lead(website="http://janespiano.com")
        assert lead.website == "http://janespiano.com"

    def test_none_stays_none(self):
        lead = make_lead(website=None)
        assert lead.website is None


class TestRatingClamping:
    def test_clamps_above_5(self):
        lead = make_lead(rating=6.0)
        assert lead.rating == 5.0

    def test_clamps_below_1(self):
        lead = make_lead(rating=0.5)
        assert lead.rating == 1.0

    def test_valid_rating_unchanged(self):
        lead = make_lead(rating=4.2)
        assert lead.rating == 4.2


class TestHelpers:
    def test_display_name_studio_preferred(self):
        lead = make_lead(studio_name="Jane's Piano Studio", teacher_name="Jane Smith")
        assert lead.display_name() == "Jane's Piano Studio"

    def test_display_name_falls_back_to_teacher(self):
        lead = make_lead(teacher_name="Jane Smith")
        assert lead.display_name() == "Jane Smith"

    def test_has_contact_phone(self):
        lead = make_lead(phone="5165551234")
        assert lead.has_contact() is True

    def test_has_contact_false_when_empty(self):
        lead = make_lead()
        assert lead.has_contact() is False

    def test_add_source_no_duplicates(self):
        lead = make_lead(source=SourceType.GOOGLE_MAPS)
        lead.add_source(SourceType.GOOGLE_MAPS)
        lead.add_source(SourceType.GOOGLE_MAPS)
        assert lead.sources.count(SourceType.GOOGLE_MAPS) == 1

    def test_add_source_new_source_appended(self):
        lead = make_lead(source=SourceType.GOOGLE_MAPS, sources=[SourceType.GOOGLE_MAPS])
        lead.add_source(SourceType.RCM)
        assert SourceType.RCM in lead.sources


class TestEnums:
    def test_lead_status_values(self):
        assert LeadStatus.NEW.value == "new"
        assert LeadStatus.TAKEN.value == "taken"

    def test_source_type_values(self):
        assert SourceType.GOOGLE_MAPS.value == "google_maps"
        assert SourceType.RCM.value == "rcm"

    def test_territory_values(self):
        assert Territory.NYC_METRO.value == "nyc_metro"
        assert Territory.LONG_ISLAND.value == "long_island"
        assert Territory.NORTH_JERSEY.value == "north_jersey"
