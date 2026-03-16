"""
Plantpriset — Base scraper with shared utilities.
All retailer scrapers inherit from this.
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7",
}


class BaseScraper:
    retailer_slug = ""
    base_url = ""
    delay = 1.5  # seconds between requests

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.all_products = []

    def get_page(self, url, timeout=15):
        resp = self.session.get(url, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser"), resp

    def parse_price(self, text):
        if not text:
            return None
        cleaned = re.sub(r'[^\d.,]', '', text.strip()).replace(",", ".")
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def deduplicate(self, products):
        seen = set()
        unique = []
        for p in products:
            key = p.get("product_url", p.get("name", ""))
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    def save(self, products):
        output_path = OUTPUT_DIR / f"{self.retailer_slug}_products.json"
        data = {
            "retailer": self.retailer_slug,
            "scraped_at": datetime.utcnow().isoformat(),
            "total_products": len(products),
            "products": products,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path

    def run(self):
        print(f"\n{'='*55}")
        print(f"PLANTPRISET — {self.retailer_slug.upper()} scraper")
        print(f"{'='*55}")

        # Warm up session with homepage cookies
        try:
            self.session.get(self.base_url, timeout=15)
            time.sleep(1)
        except Exception:
            pass

        products = self.scrape()
        unique = self.deduplicate(products)
        output_path = self.save(unique)

        prices = [p["price_sek"] for p in unique if p.get("price_sek")]
        print(f"\nDONE! {len(unique)} unique products → {output_path.name}")
        if prices:
            print(f"Prices: {min(prices):.0f} – {max(prices):.0f} kr (avg {sum(prices)/len(prices):.0f} kr)")
        return unique

    def scrape(self):
        """Override in subclass."""
        raise NotImplementedError
