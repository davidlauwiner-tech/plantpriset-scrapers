"""Cramers Blommor scraper — full catalog on single pages, data- attributes."""
import re
import time
from datetime import datetime
from .base import BaseScraper

CATEGORY_URLS = [
    "/froer/", "/froer/blommande-ettariga-annueller/", "/froer/blommande-tvariga-bienner/",
    "/froer/blommande-flerariga-perenner/", "/froer/luktart/", "/froer/palettbladsfroer/",
    "/froer/ekologiska/", "/froer/gronsaksfroer/", "/froer/froer-kryddvaxter/",
    "/froer/micro-leaf-groddar/", "/froer/grasfron/", "/froer/jora-dahl/", "/froer/nordfro/",
]


class CramersScraper(BaseScraper):
    retailer_slug = "cramers"
    base_url = "https://shop.cramersblommor.com"

    def extract_product(self, card, cat_url):
        p = {"retailer": self.retailer_slug, "category_url": cat_url}
        p["article_number"] = card.get("data-artno", "")
        p["in_stock"] = card.get("data-buyable") == "1"
        p["on_sale"] = card.get("data-iscampaign") == "1"
        data_price = card.get("data-price")
        if data_price:
            try:
                p["price_sek"] = float(data_price)
            except (ValueError, TypeError):
                pass
        p["name"] = card.get("data-title", "")
        h3 = card.select_one(".product-item__heading")
        if h3:
            p["name"] = h3.get_text(strip=True)
        latin = card.select_one(".product-item__heading--latin")
        if latin:
            p["latin_name"] = latin.get_text(strip=True)
        link = card.select_one("a[href]")
        if link:
            href = link.get("href", "")
            if href:
                p["product_url"] = f"{self.base_url}{href}" if not href.startswith("http") else href
        if not p.get("price_sek"):
            price_el = card.select_one(".price")
            if price_el:
                p["price_sek"] = self.parse_price(price_el.get_text())
        img = card.select_one("img")
        if img:
            src = img.get("src", "")
            if src:
                p["image_url"] = f"{self.base_url}{src}" if not src.startswith("http") else src
        p["scraped_at"] = datetime.utcnow().isoformat()
        return p

    def scrape(self):
        all_products = []
        for i, cat in enumerate(CATEGORY_URLS, 1):
            try:
                soup, _ = self.get_page(f"{self.base_url}{cat}", timeout=30)
                cards = soup.select(".product-item")
                count = 0
                for card in cards:
                    prod = self.extract_product(card, cat)
                    if prod.get("name") and prod.get("price_sek"):
                        all_products.append(prod)
                        count += 1
                print(f"  [{i}/{len(CATEGORY_URLS)}] {cat} → {count}")
            except Exception as e:
                print(f"  [{i}/{len(CATEGORY_URLS)}] {cat} → ERROR: {e}")
            time.sleep(self.delay)
        return all_products
