"""
scrapers/domain_crawler.py
──────────────────────────
Website crawler that:
  1. Takes a list of URLs (from Google search results, domain datasets, etc.)
  2. Visits each site (respecting robots.txt and rate limits)
  3. Detects if it's a piano teacher site using keyword matching
  4. Extracts contact info (phone, email, teacher name) from the page

This scraper is designed to be called with a list of URLs gathered
from other sources (Google search, domain datasets, etc.).
It does NOT generate its own URL list — feed it URLs from other scrapers
or from manual domain lists.

Usage:
    crawler = DomainCrawler()
    raw_leads = crawler.scrape_urls(
        urls=["https://janespiano.com", "https://pianoteachernyc.com"],
        territory=Territory.NYC_METRO,
    )
"""

from __future__ import annotations

import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm

from config.settings import (
    CRAWL_MAX_DEPTH,
    CRAWL_MAX_PAGES,
    PIANO_KEYWORDS,
    REQUEST_DELAY_SECONDS,
)
from config.territories import TerritoryConfig
from scrapers.base_scraper import BaseScraper
from storage.schema import RawLead, SourceType, Territory
from utils.helpers import extract_emails, extract_phones, extract_zip_from_address
from utils.http import get_html


class DomainCrawler(BaseScraper):
    """
    Crawls websites to identify and extract piano teacher lead info.

    This scraper is supplemental — it enriches leads found by other scrapers
    or processes domain lists from external sources (SEO tools, domain feeds).
    """

    source = SourceType.DOMAIN_CRAWL

    def scrape(
        self,
        territory: Territory,
        config: TerritoryConfig,
    ) -> list[RawLead]:
        """
        BaseScraper interface — not the primary entry point for this class.
        Use scrape_urls() directly when you have a URL list.
        """
        logger.warning(
            "DomainCrawler.scrape() called without URLs. "
            "Use scrape_urls(urls=[...], territory=...) instead."
        )
        return []

    def scrape_urls(
        self,
        urls: list[str],
        territory: Territory,
    ) -> list[RawLead]:
        """
        Crawl a list of URLs and return RawLeads for confirmed piano teacher sites.

        Args:
            urls:      List of URLs to check.
            territory: Territory to tag results with.

        Returns:
            List of RawLead objects for piano-related sites only.
        """
        self.logger.info(f"Crawling {len(urls)} URLs for territory={territory.value}")
        raw_leads: list[RawLead] = []

        for url in tqdm(urls, desc="Crawling domains", unit="url"):
            try:
                result = self._crawl_site(url, territory)
                if result:
                    raw_leads.append(result)
                    self.logger.debug(f"  ✓ Piano site found: {url}")
                else:
                    self.logger.debug(f"  ✗ Not a piano site: {url}")
            except Exception as e:
                self.logger.warning(f"  Error crawling {url}: {e}")

            time.sleep(REQUEST_DELAY_SECONDS)

        self.logger.info(f"Crawl complete: {len(raw_leads)}/{len(urls)} piano sites found")
        return raw_leads

    # ─────────────────────────────────────────
    # Core crawl logic
    # ─────────────────────────────────────────

    def _crawl_site(
        self,
        start_url: str,
        territory: Territory,
    ) -> Optional[RawLead]:
        """
        Crawl a single site up to CRAWL_MAX_DEPTH.
        Returns RawLead if piano-related, None otherwise.
        """
        if not start_url.startswith(("http://", "https://")):
            start_url = "https://" + start_url

        base_domain = self._extract_domain(start_url)
        if not base_domain:
            return None

        # Check robots.txt before crawling
        if not self._is_allowed_by_robots(start_url):
            self.logger.debug(f"robots.txt disallows crawling: {start_url}")
            return None

        # BFS crawl
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(start_url, 0)]  # (url, depth)

        # Accumulated data across all pages
        all_text = ""
        all_phones: list[str] = []
        all_emails: list[str] = []
        page_title = ""
        is_piano_site = False

        while queue and len(visited) < CRAWL_MAX_PAGES:
            url, depth = queue.pop(0)
            if url in visited or depth > CRAWL_MAX_DEPTH:
                continue
            visited.add(url)

            html = get_html(url, delay=REQUEST_DELAY_SECONDS)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            page_text = soup.get_text(separator=" ", strip=True).lower()
            all_text += " " + page_text

            # Capture title from homepage only
            if url == start_url:
                title_tag = soup.find("title")
                page_title = title_tag.get_text(strip=True) if title_tag else ""

            # Check piano keywords
            if self._is_piano_page(page_text):
                is_piano_site = True

            # Extract contact info from this page
            all_phones.extend(extract_phones(soup.get_text()))
            all_emails.extend(extract_emails(soup.get_text()))

            # Queue internal links for deeper crawl
            if depth < CRAWL_MAX_DEPTH:
                links = self._get_internal_links(soup, url, base_domain)
                # Prioritize contact/about pages
                priority = [l for l in links if any(k in l for k in ["contact", "about", "teacher"])]
                other = [l for l in links if l not in priority]
                for link in (priority + other):
                    if link not in visited:
                        queue.append((link, depth + 1))

            time.sleep(REQUEST_DELAY_SECONDS * 0.5)

        if not is_piano_site:
            return None

        # Deduplicate contact info
        unique_phones = list(dict.fromkeys(all_phones))
        unique_emails = list(dict.fromkeys(all_emails))

        # Try to extract teacher name from page title or h1
        teacher_name = self._extract_teacher_name(page_title, all_text)

        return RawLead(
            teacher_name=teacher_name,
            studio_name=page_title if page_title else None,
            phone=unique_phones[0] if unique_phones else None,
            email=unique_emails[0] if unique_emails else None,
            website=start_url,
            source=self.source.value,
            territory=territory.value,
            raw_data={
                "start_url": start_url,
                "pages_crawled": list(visited),
                "all_phones": unique_phones,
                "all_emails": unique_emails,
            },
        )

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    def _is_piano_page(self, text: str) -> bool:
        """Check if page text contains piano teacher keywords."""
        return any(kw in text for kw in PIANO_KEYWORDS)

    def _is_allowed_by_robots(self, url: str) -> bool:
        """Check robots.txt. Returns True if we're allowed (or if robots.txt is unavailable)."""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = RobotFileParser(robots_url)
            rp.read()
            return rp.can_fetch("*", url)
        except Exception:
            return True  # assume allowed if we can't read robots.txt

    def _get_internal_links(
        self,
        soup: BeautifulSoup,
        current_url: str,
        base_domain: str,
    ) -> list[str]:
        """Extract internal links from a parsed page."""
        links = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            full_url = urljoin(current_url, href)
            link_domain = self._extract_domain(full_url)
            if link_domain == base_domain:
                # Strip fragments
                full_url = full_url.split("#")[0]
                if full_url not in links:
                    links.append(full_url)
        return links

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract bare domain (no www) from URL."""
        try:
            return urlparse(url).netloc.lower().lstrip("www.")
        except Exception:
            return None

    def _extract_teacher_name(self, title: str, body_text: str) -> Optional[str]:
        """
        Heuristic: look for a personal name pattern (First Last) in the page title.
        Falls back to None if not found.
        """
        # Pattern: 2 capitalized words that aren't common site words
        skip_words = {"piano", "music", "lessons", "studio", "school", "teacher",
                      "home", "welcome", "about", "contact", "the", "and", "for"}
        words = title.split()
        # Look for adjacent capitalized words
        for i in range(len(words) - 1):
            w1, w2 = words[i].strip(".,|–-"), words[i + 1].strip(".,|–-")
            if (w1[0:1].isupper() and w2[0:1].isupper()
                    and w1.lower() not in skip_words
                    and w2.lower() not in skip_words
                    and len(w1) > 1 and len(w2) > 1):
                return f"{w1} {w2}"
        return None
