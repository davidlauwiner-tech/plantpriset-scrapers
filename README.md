# Plantpriset — Price Scrapers

Automated daily scraping of Swedish garden product retailers for [plantpriset.se](https://plantpriset.se).

## Quick Start

```bash
pip install -r requirements.txt
python run_all.py              # Run all scrapers
python run_all.py impecta zetas  # Run specific ones
```

Output goes to `output/*.json`.

## Scrapers

| Retailer | Method | Products | File |
|---|---|---|---|
| Impecta Fröhandel | HTML (requests + BS4) | ~2,250 | `impecta_products.json` |
| Blomsterlandet | HTML (requests + BS4) | ~2,450 | `blomsterlandet_products.json` |
| Cramers Blommor | HTML (requests + BS4) | ~1,850 | `cramers_products.json` |
| Zetas Trädgård | Shopify JSON API | ~900 | `zetas_products.json` |
| Klostra | HTML (requests + BS4) | ~1,200 | `klostra_products.json` |
| **Total** | | **~8,650** | |

## Automation

GitHub Actions runs all scrapers daily at 07:00 CEST via `.github/workflows/daily-scrape.yml`.

- Results are committed back to the repo in `output/`
- Also uploaded as workflow artifacts (30-day retention)
- Manual trigger available via "Run workflow" button

## Project Structure

```
plantpriset-scrapers/
├── run_all.py                 # Main entry point
├── requirements.txt
├── scrapers/
│   ├── base.py                # Shared utilities
│   ├── impecta.py
│   ├── blomsterlandet.py
│   ├── cramers.py
│   ├── zetas.py
│   └── klostra.py
├── output/                    # JSON output (auto-created)
└── .github/workflows/
    └── daily-scrape.yml       # Daily cron job
```

## Adding a New Scraper

1. Create `scrapers/myretailer.py`
2. Subclass `BaseScraper` and implement `scrape()` method
3. Register it in `run_all.py` → `ALL_SCRAPERS` dict
4. Push to GitHub — it auto-runs on next cron cycle
