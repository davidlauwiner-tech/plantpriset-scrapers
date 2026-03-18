"""Plantagen scraper — via Meilisearch API."""
import time
import json
from datetime import datetime
from .base import BaseScraper
import requests

MEILI_URL = "https://ms-a6530e77c471-12443.lon.meilisearch.io"
MEILI_KEY = "a2159774cf867351b1195f0a05a4fb9f4693c781bd3e89a3ff5e856637710594"


class PlantagenScraper(BaseScraper):
    retailer_slug = "plantagen"
    base_url = "https://plantagen.se"

    def scrape(self):
        all_products = []
        offset = 0
        batch_size = 200

        while True:
            print(f"  Fetching offset {offset}...")
            resp = requests.post(f"{MEILI_URL}/multi-search", json={
                "queries": [{
                    "indexUid": "products_sv-SE",
                    "q": "",
                    "limit": batch_size,
                    "offset": offset,
                    "attributesToRetrieve": [
                        "id", "title", "description", "image_url", "alias",
                        "sku", "discount", "market_price", "categories", "filterable"
                    ],
                }]
            }, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {MEILI_KEY}",
            }, timeout=15)

            if resp.status_code != 200:
                print(f"  HTTP {resp.status_code} — stopping")
                break

            data = resp.json()
            hits = data.get("results", [{}])[0].get("hits", [])

            if not hits:
                break

            for h in hits:
                price_se = None
                mp = h.get("market_price")
                if isinstance(mp, dict):
                    price_se = mp.get("se")
                elif isinstance(mp, (int, float)):
                    price_se = float(mp)

                brand = ""
                filterable = h.get("filterable") or {}
                if isinstance(filterable, dict):
                    brand = filterable.get("brand", "")

                cats = h.get("categories") or {}
                cat_str = json.dumps(cats).lower()
                cat_lvl1 = ""
                if isinstance(cats, dict):
                    lvl1 = cats.get("lvl1", [])
                    if lvl1 and isinstance(lvl1, list):
                        cat_lvl1 = lvl1[0]

                alias = h.get("alias", "")
                product_url = f"{self.base_url}/se/p{alias}" if alias else ""

                p = {
                    "retailer": self.retailer_slug,
                    "name": h.get("title", ""),
                    "price_sek": price_se,
                    "product_url": product_url,
                    "image_url": h.get("image_url", ""),
                    "brand": brand,
                    "article_number": h.get("sku", ""),
                    "category_url": cat_lvl1,
                    "in_stock": True,
                    "scraped_at": datetime.utcnow().isoformat(),
                }

                if p.get("name") and p.get("price_sek"):
                    all_products.append(p)

            print(f"  Got {len(hits)} products (total: {len(all_products)})")

            if len(hits) < batch_size:
                break

            offset += batch_size
            time.sleep(1)

        return all_products
