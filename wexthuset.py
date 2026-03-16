import time, re, requests
from playwright.sync_api import sync_playwright
from base_scraper import BaseScraper

class WexthusetScraper(BaseScraper):
    retailer_slug = "wexthuset"
    retailer_name = "Wexthuset"
    retailer_url = "https://www.wexthuset.com"

    def search(self, plant):
        results = []
        for query in [plant.get("common_name_sv",""), plant.get("latin_name","")]:
            if not query: continue
            found = self._search(query)
            results.extend(found)
            if results: break
            time.sleep(1.5)
        return results

    def _search(self, query):
        try:
            url = f"https://www.wexthuset.com/search?q={requests.utils.quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (compatible; Plantpriset/1.0)"}
            r = requests.get(url, headers=headers, timeout=15)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            products = []
            for card in soup.select(".product-item, .product-card, li.product, article[class*='product']")[:5]:
                name_el = card.select_one("h2,h3,.product-name,[class*='name'],[class*='title']")
                price_el = card.select_one(".price,[class*='price']")
                link_el = card.select_one("a[href]")
                name = name_el.get_text(strip=True) if name_el else ""
                price = self.parse_price(price_el.get_text(strip=True) if price_el else "")
                href = link_el["href"] if link_el else ""
                if href and not href.startswith("http"): href = self.retailer_url + href
                if name and price and href:
                    products.append({"name":name,"price":price,"url":href,"in_stock":True})
            return products
        except Exception as e:
            print(f"  Error: {e}")
            return []

if __name__ == "__main__":
    WexthusetScraper().run()
