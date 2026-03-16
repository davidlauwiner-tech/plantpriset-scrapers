"""Klostra scraper — Magento store with data-price-amount attributes."""
import time
from datetime import datetime
from .base import BaseScraper

CATEGORY_URLS = ["/froer"]


class KlostraScraper(BaseScraper):
    retailer_slug = "klostra"
    base_url = "https://www.klostra.se"

    def scrape_category(self, path):
        products = []
        page = 1
        while True:
            url = f"{self.base_url}{path}" + (f"?p={page}" if page > 1 else "")
            try:
                soup, _ = self.get_page(url)
                cards = soup.select("li.product-item")
                if not cards:
                    break
                before = len(products)
                for card in cards:
                    p = {"retailer": self.retailer_slug, "category_url": path}
                    name_el = card.select_one(".product-item-link")
                    if name_el:
                        p["name"] = name_el.get_text(strip=True).replace("Blomfröer", "").replace("Grönsaksfröer", "").strip()
                        href = name_el.get("href", "")
                        if href:
                            p["product_url"] = href
                    price_el = card.select_one("[data-price-amount]")
                    if price_el:
                        try:
                            p["price_sek"] = float(price_el["data-price-amount"])
                        except (ValueError, TypeError):
                            pass
                    img = card.select_one("img.product-image-photo")
                    if img:
                        p["image_url"] = img.get("src", "")
                    stock_el = card.select_one(".product-availability-info")
                    if stock_el:
                        p["in_stock"] = "lager" in stock_el.get_text().lower()
                    p["scraped_at"] = datetime.utcnow().isoformat()
                    if p.get("name") and p.get("price_sek"):
                        products.append(p)
                if len(products) == before:
                    break
                next_link = soup.select_one(f'a[href*="p={page + 1}"]')
                if next_link:
                    page += 1
                    time.sleep(self.delay)
                else:
                    break
            except Exception as e:
                print(f"    ERROR page {page}: {e}")
                break
        return products, page

    def scrape(self):
        all_products = []
        for i, cat in enumerate(CATEGORY_URLS, 1):
            products, pages = self.scrape_category(cat)
            pg = f" ({pages}p)" if pages > 1 else ""
            print(f"  [{i}/{len(CATEGORY_URLS)}] {cat} → {len(products)}{pg}")
            all_products.extend(products)
            time.sleep(self.delay)
        return all_products
