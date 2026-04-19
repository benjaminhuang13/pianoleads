"""
scrapers/base_scraper.py
────────────────────────
Abstract base class for all scrapers.

Every scraper must:
  1. Inherit from BaseScraper
  2. Set `source` class attribute (SourceType enum value)
  3. Implement `scrape(territory, config)` → list[RawLead]

The scrape() method should:
  - Yield/return RawLead objects (not Lead objects — normalization happens later)
  - Log progress with self.logger
  - Handle errors gracefully (catch per-item, not whole run)
  - Never write to disk directly

Example:
    class MyNewScraper(BaseScraper):
        source = SourceType.THUMBTACK

        def scrape(self, territory, config):
            raw_leads = []
            for city in config.search_city_names:
                # ... fetch and parse ...
                raw_leads.append(RawLead(
                    studio_name="Jane's Piano",
                    phone="5165551234",
                    source=self.source.value,
                    territory=territory.value,
                ))
            return raw_leads
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from loguru import logger

from config.territories import TerritoryConfig
from storage.schema import RawLead, SourceType, Territory


class BaseScraper(ABC):
    """
    Abstract base class for all lead scrapers.
    Subclasses implement `scrape()` and set `source`.
    """

    # Must be set by subclasses
    source: SourceType = NotImplemented

    def __init__(self) -> None:
        if self.source is NotImplemented:
            raise NotImplementedError(f"{self.__class__.__name__} must define `source`")
        self.logger = logger.bind(scraper=self.__class__.__name__)

    @abstractmethod
    def scrape(
        self,
        territory: Territory,
        config: TerritoryConfig,
    ) -> list[RawLead]:
        """
        Run the scraper for a given territory.

        Args:
            territory: The Territory enum value being scraped.
            config:    The TerritoryConfig with ZIP codes, search areas, etc.

        Returns:
            List of RawLead objects. May be empty if no results found.
        """
        ...

    def run(
        self,
        territory: Territory,
        config: TerritoryConfig,
    ) -> list[RawLead]:
        """
        Public entry point. Wraps scrape() with top-level error handling
        and logging so callers don't need to worry about it.
        """
        self.logger.info(f"Starting scrape | territory={territory.value}")
        try:
            results = self.scrape(territory, config)
            self.logger.info(
                f"Scrape complete | territory={territory.value} | found={len(results)}"
            )
            return results
        except Exception as e:
            self.logger.error(f"Scraper failed | territory={territory.value} | error={e}")
            raise
