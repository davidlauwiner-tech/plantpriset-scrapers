#!/usr/bin/env python3
"""
Plantpriset — Run all scrapers.

Usage:
    python run_all.py                # Run all scrapers
    python run_all.py impecta zetas  # Run specific scrapers only
"""
import sys
import time
from datetime import datetime

from scrapers.impecta import ImpectaScraper
from scrapers.blomsterlandet import BlomsterlandetScraper
from scrapers.cramers import CramersScraper
from scrapers.zetas import ZetasScraper
from scrapers.klostra import KlostraScraper
from scrapers.plantagen import PlantagenScraper
from scrapers.granngarden import GranggardenScraper

ALL_SCRAPERS = {
    "impecta": ImpectaScraper,
    "blomsterlandet": BlomsterlandetScraper,
    "cramers": CramersScraper,
    "zetas": ZetasScraper,
    "klostra": KlostraScraper,
    "plantagen": PlantagenScraper,
    "granngarden": GranggardenScraper,
}


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(ALL_SCRAPERS.keys())
    scrapers_to_run = {k: v for k, v in ALL_SCRAPERS.items() if k in requested}

    if not scrapers_to_run:
        print(f"Unknown scrapers: {requested}")
        print(f"Available: {list(ALL_SCRAPERS.keys())}")
        sys.exit(1)

    print(f"{'#'*55}")
    print(f"# PLANTPRISET — Daily Price Scrape")
    print(f"# {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"# Scrapers: {', '.join(scrapers_to_run.keys())}")
    print(f"{'#'*55}")

    results = {}
    total_products = 0
    total_start = time.time()

    for name, scraper_class in scrapers_to_run.items():
        start = time.time()
        try:
            scraper = scraper_class()
            products = scraper.run()
            elapsed = time.time() - start
            results[name] = {"products": len(products), "status": "ok", "time": f"{elapsed:.0f}s"}
            total_products += len(products)
        except Exception as e:
            elapsed = time.time() - start
            results[name] = {"products": 0, "status": f"FAILED: {e}", "time": f"{elapsed:.0f}s"}
            print(f"\n  FAILED: {e}")

    total_elapsed = time.time() - total_start

    print(f"\n{'='*55}")
    print(f"SCRAPE COMPLETE — {total_products} total products in {total_elapsed:.0f}s")
    print(f"{'='*55}")
    for name, result in results.items():
        status = "✅" if result["status"] == "ok" else "❌"
        print(f"  {status} {name:20s} {result['products']:>6} products  ({result['time']})")
    print()


if __name__ == "__main__":
    main()
