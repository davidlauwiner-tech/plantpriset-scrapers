"""Blomsterlandet scraper — server-rendered HTML with pagination."""
import re
import time
from datetime import datetime
from .base import BaseScraper

CATEGORY_URLS = [
    "/produkter/vaxter/froer/gronsaksfroer/bonor-arter/",
    "/produkter/vaxter/froer/gronsaksfroer/chili-paprika/",
    "/produkter/vaxter/froer/gronsaksfroer/groddar/",
    "/produkter/vaxter/froer/gronsaksfroer/gurka-melon/",
    "/produkter/vaxter/froer/gronsaksfroer/kalvaxter/",
    "/produkter/vaxter/froer/gronsaksfroer/lokvaxter/",
    "/produkter/vaxter/froer/gronsaksfroer/pumpa-squash/",
    "/produkter/vaxter/froer/gronsaksfroer/rotfrukter/",
    "/produkter/vaxter/froer/gronsaksfroer/sallat-bladvaxter/",
    "/produkter/vaxter/froer/gronsaksfroer/tomat-aubergin/",
    "/produkter/vaxter/froer/gronsaksfroer/ovriga-gronsaksfroer/",
    "/produkter/vaxter/froer/blomsterfroer/",
    "/produkter/vaxter/froer/kryddfroer/",
    "/produkter/vaxter/froer/angsfroer/",
    "/produkter/vaxter/utomhus/perenner/",
    "/produkter/vaxter/utomhus/rosor/",
    "/produkter/vaxter/utomhus/buskar/",
    "/produkter/vaxter/utomhus/trad/",
    "/produkter/vaxter/utomhus/klattervaxter/",
    "/produkter/vaxter/utomhus/prydnadsgras/",
    "/produkter/vaxter/utomhus/barr/",
    "/produkter/vaxter/utomhus/lokar/",
    "/produkter/vaxter/inomhus/",
    "/produkter/tillbehor/jord-godsel-naring/",
    "/produkter/tillbehor/krukor-ytterkrukor/",
    "/produkter/tillbehor/odling-drivhus/",
    "/produkter/tillbehor/redskap-verktyg/",
    "/produkter/tillbehor/bevattning/",
    "/produkter/tillbehor/vaxtskydd/",
    "/produkter/tillbehor/vaxtbelysning/",
]


class BlomsterlandetScraper(BaseScraper):
    retailer_slug = "blomsterlandet"
    base_url = "https://www.blomsterlandet.se"

    def extract_product(self, card, cat_url):
        p = {"retailer": self.retailer_slug, "category_url": cat_url}
        name_el = card.select_one("h2")
        if name_el:
            p["name"] = name_el.get_text(strip=True)
        brand_el = card.select_one("p[class*='ProductDescriptor']")
        if brand_el:
            p["brand"] = brand_el.get_text(strip=True)
        parent_link = card.find_parent("a")
        if parent_link:
            href = parent_link.get("href", "")
            if href:
                p["product_url"] = f"{self.base_url}{href}" if not href.startswith("http") else href
        kr_el = card.select_one("[class*='Normal-sc']")
        ore_el = card.select_one("[class*='Elevated-sc']")
        if kr_el:
            kr = kr_el.get_text(strip=True)
            ore = ore_el.get_text(strip=True) if ore_el else "00"
            try:
                p["price_sek"] = float(f"{kr}.{ore}")
            except (ValueError, TypeError):
                pass
        img = card.select_one("img")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src:
                p["image_url"] = src if src.startswith("http") else f"{self.base_url}{src}"
        p["scraped_at"] = datetime.utcnow().isoformat()
        return p

    def scrape_category(self, cat_url):
        products = []
        page_num = 1
        while True:
            url = f"{self.base_url}{cat_url}"
            if page_num > 1:
                sep = "&" if "?" in cat_url else "?"
                url = f"{self.base_url}{cat_url}{sep}page={page_num}&sorting=Name"
            try:
                soup, _ = self.get_page(url)
                cards = soup.select(".wrapper-big-card")
                if not cards:
                    break
                for card in cards:
                    prod = self.extract_product(card, cat_url)
                    if prod.get("name") and prod.get("price_sek"):
                        products.append(prod)
                next_link = soup.select_one(f'a[href*="page={page_num + 1}"]')
                if next_link:
                    page_num += 1
                    time.sleep(self.delay)
                else:
                    break
            except Exception as e:
                print(f"    ERROR page {page_num}: {e}")
                break
        return products, page_num

    def scrape(self):
        all_products = []
        for i, cat in enumerate(CATEGORY_URLS, 1):
            products, pages = self.scrape_category(cat)
            pg = f" ({pages}p)" if pages > 1 else ""
            print(f"  [{i}/{len(CATEGORY_URLS)}] {cat} → {len(products)}{pg}")
            all_products.extend(products)
            time.sleep(self.delay)
        return all_products
