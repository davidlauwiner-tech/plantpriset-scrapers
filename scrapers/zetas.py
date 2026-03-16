"""Zetas Trädgård scraper — Shopify JSON API (no HTML parsing needed)."""
import time
from datetime import datetime
from .base import BaseScraper


class ZetasScraper(BaseScraper):
    retailer_slug = "zetas"
    base_url = "https://zetas.se"

    def scrape(self):
        all_products = []
        page = 1
        while True:
            url = f"{self.base_url}/products.json?limit=250&page={page}"
            print(f"  Fetching page {page}...")
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code != 200:
                    break
                data = resp.json()
                products = data.get("products", [])
                if not products:
                    break
                for sp in products:
                    variants = sp.get("variants", [])
                    price = None
                    if variants:
                        try:
                            price = float(variants[0].get("price", 0))
                        except (ValueError, TypeError):
                            pass
                    p = {
                        "retailer": self.retailer_slug,
                        "name": sp.get("title", ""),
                        "product_url": f"{self.base_url}/products/{sp.get('handle', '')}",
                        "price_sek": price,
                        "product_type": sp.get("product_type", ""),
                        "brand": sp.get("vendor", ""),
                        "tags": sp.get("tags", []),
                        "image_url": sp.get("images", [{}])[0].get("src", "") if sp.get("images") else "",
                        "in_stock": variants[0].get("available", False) if variants else False,
                        "article_number": variants[0].get("sku", "") if variants else "",
                        "scraped_at": datetime.utcnow().isoformat(),
                    }
                    if p.get("name") and p.get("price_sek"):
                        all_products.append(p)
                print(f"  Page {page}: {len(products)} products")
                if len(products) < 250:
                    break
                page += 1
                time.sleep(self.delay)
            except Exception as e:
                print(f"  Page {page} ERROR: {e}")
                break
        return all_products
