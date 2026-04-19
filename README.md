# 🎹 Piano Lead Finder

A modular lead generation tool for piano sales reps. Scrapes, deduplicates, enriches, and stores piano teacher leads across NYC Metro, Long Island, and North Jersey.

## Project Structure

```
piano-leads/
├── config/
│   ├── settings.py          # All configuration (API keys, territories, thresholds)
│   └── territories.py       # ZIP codes and search areas per territory
├── scrapers/
│   ├── base_scraper.py      # Abstract base class all scrapers inherit from
│   ├── google_maps.py       # Google Maps Places API scraper
│   └── domain_crawler.py    # Website crawler + keyword detector
├── processors/
│   ├── deduplicator.py      # Detects duplicate leads (name/phone/domain)
│   ├── enricher.py          # WHOIS lookup, score calculation
│   └── normalizer.py        # Cleans/normalizes raw data into Lead objects
├── storage/
│   ├── schema.py            # Pydantic Lead model (the source of truth)
│   ├── store.py             # JSON read/write + ID management
│   └── exporter.py          # CSV export
├── utils/
│   ├── http.py              # Retry-aware HTTP client with rate limiting
│   ├── logger.py            # Centralized logging setup
│   └── helpers.py           # Phone/email normalization, text utilities
├── output/                  # Generated JSON and CSV files (gitignored)
├── logs/                    # Log files (gitignored)
├── tests/                   # Unit tests per module
├── main.py                  # CLI entry point
├── .env.example             # Environment variable template
└── requirements.txt
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and fill in your API keys
cp .env.example .env

# 3. Run a scrape
python main.py scrape --source google_maps --territory nyc_metro
python main.py scrape --source google_maps --territory long_island
python main.py scrape --source google_maps --territory north_jersey

# 4. Export leads to CSV
python main.py export --format csv --output output/leads.csv

# 5. Show lead stats
python main.py stats
```

## Adding a New Scraper

1. Create `scrapers/your_source.py`
2. Inherit from `BaseScraper`
3. Implement `scrape()` → returns `List[RawLead]`
4. Register it in `main.py`'s source map

## Data Flow

```
Scraper → RawLead → Normalizer → Lead (schema) → Deduplicator → Store → Enricher
```
