"""
scrapers/google_maps.py
───────────────────────
Google Maps Places API scraper.

Uses two complementary approaches:
  1. Nearby Search — grid of lat/lng circles covering each territory
  2. Text Search  — city name + search term queries for broader coverage

Both pull Place Details for every result to get phone, website, hours, etc.

API calls used:
  - places.nearby_search()  → finds places near a point
  - places.places()         → text-based search
  - places.place()          → place details (phone, website, reviews, etc.)

Google Maps pricing note (as of 2024):
  - Nearby/Text Search: $0.032/request
  - Place Details: $0.017/request
  Budget accordingly — each scrape run across 3 territories ≈ 200–400 API calls.

Requires: GOOGLE_MAPS_API_KEY in .env
"""

from __future__ import annotations

import time
from typing import Optional

import googlemaps
from loguru import logger
from tqdm import tqdm

from config.settings import (
    GMAPS_MAX_RESULTS_PER_QUERY,
    GMAPS_SEARCH_TERMS,
    GOOGLE_MAPS_API_KEY,
    REQUEST_DELAY_SECONDS,
)
from config.territories import TerritoryConfig
from scrapers.base_scraper import BaseScraper
from storage.schema import RawLead, SourceType, Territory


# Place Detail fields to request (controls cost — only pay for what you use)
# See: https://developers.google.com/maps/documentation/places/web-service/details#fields
PLACE_DETAIL_FIELDS = [
    "name",
    "formatted_address",
    "formatted_phone_number",
    "international_phone_number",
    "website",
    "rating",
    "user_ratings_total",
    "photos",
    "reviews",
    "place_id",
    "geometry",
    "types",
    "business_status",
]


class GoogleMapsScraper(BaseScraper):
    """
    Scrapes piano teacher leads from Google Maps Places API.

    Combines nearby search (geographic circles) with text search (city names)
    to maximize coverage, then deduplicates by place_id before fetching details.
    """

    source = SourceType.GOOGLE_MAPS

    def __init__(self) -> None:
        super().__init__()
        if not GOOGLE_MAPS_API_KEY:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY not set. Add it to your .env file.\n"
                "Get a key at: https://console.cloud.google.com"
            )
        self._client = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    # ─────────────────────────────────────────
    # Main scrape entry point
    # ─────────────────────────────────────────

    def scrape(
        self,
        territory: Territory,
        config: TerritoryConfig,
    ) -> list[RawLead]:
        """
        Run nearby search + text search, then fetch details for each result.
        Returns deduplicated RawLead objects.
        """
        # Step 1: Collect all unique place_ids across all search strategies
        place_ids: set[str] = set()

        self.logger.info(f"Running nearby search across {len(config.search_circles)} circles...")
        for circle in config.search_circles:
            for term in GMAPS_SEARCH_TERMS:
                ids = self._nearby_search(
                    lat=circle.lat,
                    lng=circle.lng,
                    radius=circle.radius_meters,
                    keyword=term,
                    label=circle.label,
                )
                place_ids.update(ids)
                time.sleep(REQUEST_DELAY_SECONDS)

        self.logger.info(f"Running text search across {len(config.search_city_names)} cities...")
        for city in config.search_city_names:
            for term in GMAPS_SEARCH_TERMS:
                query = f"{term} {city}"
                ids = self._text_search(query)
                place_ids.update(ids)
                time.sleep(REQUEST_DELAY_SECONDS)

        self.logger.info(f"Found {len(place_ids)} unique places. Fetching details...")

        # Step 2: Fetch details for each place and build RawLeads
        raw_leads: list[RawLead] = []
        for place_id in tqdm(place_ids, desc="Fetching place details", unit="place"):
            raw = self._fetch_place_details(place_id, territory)
            if raw:
                raw_leads.append(raw)
            time.sleep(REQUEST_DELAY_SECONDS)

        return raw_leads

    # ─────────────────────────────────────────
    # Search methods
    # ─────────────────────────────────────────

    def _nearby_search(
        self,
        lat: float,
        lng: float,
        radius: int,
        keyword: str,
        label: str = "",
    ) -> set[str]:
        """
        Run a Google Places nearby search and return all place_ids found.
        Paginates through all results (up to GMAPS_MAX_RESULTS_PER_QUERY).
        """
        place_ids: set[str] = set()
        location = (lat, lng)
        page_token: Optional[str] = None
        count = 0

        self.logger.debug(f"Nearby search: '{keyword}' near {label or location}")

        while count < GMAPS_MAX_RESULTS_PER_QUERY:
            try:
                kwargs = {
                    "location": location,
                    "radius": radius,
                    "keyword": keyword,
                    "type": "point_of_interest",
                }
                if page_token:
                    # Google requires a short delay before using a page token
                    time.sleep(2)
                    kwargs["page_token"] = page_token

                result = self._client.places_nearby(**kwargs)
                results = result.get("results", [])

                for place in results:
                    pid = place.get("place_id")
                    if pid:
                        place_ids.add(pid)

                count += len(results)
                page_token = result.get("next_page_token")
                if not page_token:
                    break

            except googlemaps.exceptions.ApiError as e:
                self.logger.error(f"Google Maps API error in nearby search: {e}")
                break

        self.logger.debug(f"  → {len(place_ids)} places found near {label or location}")
        return place_ids

    def _text_search(self, query: str) -> set[str]:
        """
        Run a Google Places text search and return place_ids.
        Paginates up to GMAPS_MAX_RESULTS_PER_QUERY results.
        """
        place_ids: set[str] = set()
        page_token: Optional[str] = None
        count = 0

        self.logger.debug(f"Text search: '{query}'")

        while count < GMAPS_MAX_RESULTS_PER_QUERY:
            try:
                kwargs = {"query": query}
                if page_token:
                    time.sleep(2)
                    kwargs["page_token"] = page_token

                result = self._client.places(**kwargs)
                results = result.get("results", [])

                for place in results:
                    pid = place.get("place_id")
                    if pid:
                        place_ids.add(pid)

                count += len(results)
                page_token = result.get("next_page_token")
                if not page_token:
                    break

            except googlemaps.exceptions.ApiError as e:
                self.logger.error(f"Google Maps API error in text search '{query}': {e}")
                break

        self.logger.debug(f"  → {len(place_ids)} places for '{query}'")
        return place_ids

    # ─────────────────────────────────────────
    # Place detail fetching
    # ─────────────────────────────────────────

    def _fetch_place_details(
        self,
        place_id: str,
        territory: Territory,
    ) -> Optional[RawLead]:
        """
        Fetch full details for a single place_id and return a RawLead.
        Returns None if the place doesn't look like a piano teacher lead.
        """
        try:
            result = self._client.place(
                place_id=place_id,
                fields=PLACE_DETAIL_FIELDS,
            )
            place = result.get("result", {})
        except googlemaps.exceptions.ApiError as e:
            self.logger.error(f"Place details API error for {place_id}: {e}")
            return None

        if not place:
            return None

        # Filter: only keep results that seem relevant
        if not self._is_piano_related(place):
            self.logger.debug(f"  Skipping non-piano place: {place.get('name', '?')}")
            return None

        # Extract most recent review date
        most_recent_review = self._extract_most_recent_review(place)

        # Extract photo count
        photo_count = str(len(place.get("photos", [])))

        raw = RawLead(
            studio_name=place.get("name"),
            phone=place.get("formatted_phone_number") or place.get("international_phone_number"),
            website=place.get("website"),
            address=place.get("formatted_address"),
            zip_code=self._extract_zip(place.get("formatted_address", "")),
            google_place_id=place_id,
            rating=str(place.get("rating", "")),
            review_count=str(place.get("user_ratings_total", "")),
            most_recent_review=most_recent_review,
            photo_count=photo_count,
            source=self.source.value,
            territory=territory.value,
            raw_data=place,
        )

        self.logger.debug(f"  ✓ {raw.studio_name} | {raw.phone or 'no phone'} | rating={raw.rating}")
        return raw

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    def _is_piano_related(self, place: dict) -> bool:
        """
        Basic relevance filter. Checks name and types.
        Not perfect — the normalizer/enricher do deeper filtering.
        """
        piano_keywords = {"piano", "music", "lesson", "teacher", "studio", "conservatory"}
        name = (place.get("name") or "").lower()

        # Check if name contains piano-related keywords
        if any(kw in name for kw in piano_keywords):
            return True

        # Check Google place types
        types = set(place.get("types", []))
        music_types = {"music_school", "school", "point_of_interest", "establishment"}
        if types & {"music_school"}:
            return True

        # If we got here, be liberal — better to include and filter later
        # (we've already searched for piano-related terms, so most results are relevant)
        return True

    def _extract_most_recent_review(self, place: dict) -> Optional[str]:
        """Extract the most recent review timestamp from place details."""
        reviews = place.get("reviews", [])
        if not reviews:
            return None
        # Google returns reviews sorted by relevance — sort by time ourselves
        timestamps = [r.get("time", 0) for r in reviews if r.get("time")]
        if not timestamps:
            return None
        most_recent = max(timestamps)
        # Convert Unix timestamp to ISO string
        from datetime import datetime
        return datetime.utcfromtimestamp(most_recent).isoformat()

    def _extract_zip(self, address: str) -> Optional[str]:
        """Extract ZIP code from a formatted address string."""
        import re
        match = re.search(r"\b(\d{5})(?:-\d{4})?\b", address)
        return match.group(1) if match else None
