"""Granngården scraper — HTML parsing + price API."""
import re
import time
import json
from datetime import datetime
from .base import BaseScraper
from bs4 import BeautifulSoup

SEARCH_QUERIES = [
    "fröer tomat", "fröer gurka", "fröer paprika", "fröer chili",
    "fröer sallat", "fröer morot", "fröer basilika", "fröer dill",
    "fröer pumpa", "fröer squash", "fröer böna", "fröer ärter",
    "fröer lök", "fröer kål", "fröer broccoli", "fröer blomma",
    "fröer solros", "fröer zinnia", "fröer luktärt", "fröer kryddor",
    "fröer rädisa", "fröer spenat", "fröer persilja", "fröer rucola",
    "fröer mangold", "fröer aubergin", "fröer melon", "fröer majs",
    "sättpotatis", "sättlök", "blomsterlök", "dahlia knöl",
    "planteringsjord", "gödsel", "växtnäring", "kompost",
    "trädgårdsredskap", "sekatör", "bevattning", "vattenslang",
    "krukor utomhus", "odlingslåda", "pallkrage",
    "växtskydd", "drivhus", "växthus", "växtbelysning",
    "perenner", "buskar", "häckväxter", "rosor",
    "gräsfrö", "gräsmatta",
]


class GranggardenScraper(BaseScraper):
    retailer_slug = "granngarden"
    base_url = "https://www.granngarden.se"

    def scrape_search(self, query):
        """Search, extract product numbers, fetch prices."""
        products = []
        try:
            resp = self.session.get(f"{self.base_url}/sok?q={query}", timeout=15)
            if resp.status_code != 200:
                return []

            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".product-card")

            if not cards:
                return []

            # Extract ALL productNumber occurrences from HTML
            # They appear as "productNumber":"1265771" in embedded JSON
            all_nums = re.findall(r'"productNumber"\s*:\s*"(\d+)"', html)
            # Deduplicate while preserving order
            seen = set()
            unique_nums = []
            for n in all_nums:
                if n not in seen:
                    seen.add(n)
                    unique_nums.append(n)

            # Fetch prices for all product numbers
            price_map = {}
            if unique_nums:
                nums_str = ",".join(unique_nums)
                try:
                    price_resp = self.session.get(
                        f"{self.base_url}/api/price/bestprice?productNumbers={nums_str}",
                        timeout=10
                    )
                    if price_resp.status_code == 200:
                        for p in price_resp.json().get("prices", []):
                            price_map[p["productNumber"]] = p["price"]
                except Exception:
                    pass

            # Match cards to product numbers (they appear in same order)
            for idx, card in enumerate(cards):
                name_el = card.select_one(".product-card__name")
                link_el = card.select_one("a.product-card__link, a")
                img_el = card.select_one("img")

                if not name_el:
                    continue

                name = name_el.get_text(strip=True)
                href = link_el.get("href", "") if link_el else ""
                img = img_el.get("src", "") if img_el else ""

                # Product number is the idx-th unique number
                prod_num = unique_nums[idx] if idx < len(unique_nums) else ""
                price = price_map.get(prod_num)

                # Extract brand from name
                brand = ""
                for bp in ["Nelson Garden", "Impecta", "Weibulls", "Hasselfors",
                           "Gardena", "Fiskars", "Omnia Garden"]:
                    if bp.lower() in name.lower():
                        brand = bp
                        break

                # Determine category from name
                cat = ""
                name_lower = name.lower()
                if "fröer" in name_lower or "frö" in name_lower:
                    cat = "froer"
                elif any(x in name_lower for x in ["jord", "gödsel", "näring"]):
                    cat = "tillbehor"
                elif any(x in name_lower for x in ["redskap", "sekatör", "sax"]):
                    cat = "tillbehor"

                # Detect multi-packs (e.g. "6-PACK", "15-pack", "3-pack")
                quantity = 1
                pack_match = re.search(r'(\d+)\s*-?\s*(?:pack|st|styck)', name, re.IGNORECASE)
                if pack_match:
                    quantity = int(pack_match.group(1))
                # Also check for "jfr pris X kr/st" pattern in price data
                effective_price = price
                if quantity > 1 and price:
                    effective_price = round(price / quantity, 2)

                p = {
                    "retailer": self.retailer_slug,
                    "name": name,
                    "price_sek": effective_price,
                    "product_url": f"{self.base_url}{href}" if href and not href.startswith("http") else href,
                    "image_url": img,
                    "brand": brand,
                    "article_number": prod_num,
                    "category_url": cat,
                    "in_stock": True,
                    "quantity": quantity,
                    "scraped_at": datetime.utcnow().isoformat(),
                }

                if p.get("name") and p.get("price_sek"):
                    products.append(p)

        except Exception as e:
            print(f"    ERROR '{query}': {e}")

        return products

    def scrape(self):
        all_products = []
        for i, query in enumerate(SEARCH_QUERIES, 1):
            products = self.scrape_search(query)
            print(f"  [{i}/{len(SEARCH_QUERIES)}] '{query}' -> {len(products)}")
            all_products.extend(products)
            time.sleep(2)
        return all_products
