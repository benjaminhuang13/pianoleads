"""
tests/test_helpers.py
─────────────────────
Unit tests for utils/helpers.py — pure functions, no side effects.
"""

import pytest
from utils.helpers import (
    clean_text,
    extract_domain,
    extract_emails,
    extract_phones,
    extract_zip_from_address,
    format_phone_display,
    is_same_domain,
    normalize_phone,
    title_case_name,
)


class TestPhoneHelpers:
    def test_extract_phones_from_text(self):
        text = "Call us at (516) 555-1234 or 718.555.5678"
        phones = extract_phones(text)
        assert "5165551234" in phones
        assert "7185555678" in phones

    def test_extract_phone_with_country_code(self):
        phones = extract_phones("+1 (212) 555-0001")
        assert "2125550001" in phones

    def test_normalize_phone_standard(self):
        assert normalize_phone("(516) 555-1234") == "5165551234"

    def test_normalize_phone_with_dashes(self):
        assert normalize_phone("516-555-1234") == "5165551234"

    def test_normalize_phone_drops_country_code(self):
        assert normalize_phone("15165551234") == "5165551234"

    def test_normalize_phone_short_returns_none(self):
        assert normalize_phone("555-1234") is None

    def test_normalize_phone_none(self):
        assert normalize_phone(None) is None

    def test_format_phone_display(self):
        assert format_phone_display("5165551234") == "(516) 555-1234"

    def test_format_phone_display_bad_input_unchanged(self):
        assert format_phone_display("bad") == "bad"


class TestEmailHelpers:
    def test_extract_email_basic(self):
        emails = extract_emails("Contact jane@pianostudio.com for info")
        assert "jane@pianostudio.com" in emails

    def test_extract_multiple_emails(self):
        emails = extract_emails("info@studio.com and lessons@piano.net")
        assert len(emails) == 2

    def test_extract_email_deduplicates(self):
        emails = extract_emails("email: info@studio.com, also info@studio.com")
        assert emails.count("info@studio.com") == 1

    def test_no_emails_returns_empty(self):
        assert extract_emails("no email here") == []


class TestDomainHelpers:
    def test_extract_domain_full_url(self):
        assert extract_domain("https://www.janespiano.com/lessons") == "janespiano.com"

    def test_extract_domain_no_www(self):
        assert extract_domain("https://janespiano.com") == "janespiano.com"

    def test_extract_domain_no_scheme(self):
        assert extract_domain("janespiano.com") == "janespiano.com"

    def test_extract_domain_none_input(self):
        assert extract_domain(None) is None

    def test_extract_domain_empty_string(self):
        assert extract_domain("") is None

    def test_is_same_domain_matching(self):
        assert is_same_domain(
            "https://www.janespiano.com/lessons",
            "https://janespiano.com/contact"
        ) is True

    def test_is_same_domain_different(self):
        assert is_same_domain(
            "https://janespiano.com",
            "https://otherstudio.com"
        ) is False


class TestTextHelpers:
    def test_clean_text_collapses_whitespace(self):
        assert clean_text("  hello   world  ") == "hello world"

    def test_clean_text_none(self):
        assert clean_text(None) is None

    def test_clean_text_empty(self):
        assert clean_text("") is None

    def test_title_case_name(self):
        assert title_case_name("jane smith") == "Jane Smith"

    def test_title_case_name_none(self):
        assert title_case_name(None) is None


class TestZipExtraction:
    def test_extract_zip_from_address(self):
        assert extract_zip_from_address("123 Main St, Garden City, NY 11530") == "11530"

    def test_extract_zip_with_plus4(self):
        assert extract_zip_from_address("456 Oak Ave, Huntington, NY 11743-2201") == "11743"

    def test_extract_zip_not_found(self):
        assert extract_zip_from_address("No zip here") is None

    def test_extract_zip_none_input(self):
        assert extract_zip_from_address(None) is None
