import os, time, re, requests
from playwright.sync_api import sync_playwright
from base_scraper import BaseScraper

class WexthusetScraper(BaseScraper):
    retailer_slug = "wexthuset"
    retailer_name = "Wexthuset"
    retailer_url = "https://www.wexthuset.com"

    def run(self):
        print(f"=== {self.retailer_name} Scraper ===")
        plants = self.get_all_plants()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
            for i, plant in enumerate(plants):
                name = plant.get("common_name_sv") or plant.get("slug")
                print(f"\n[{i+1}/{len(plants)}] {name}")
                try:
                    products = self._search(page, plant)
                    if products:
                        for prod in sorted(products, key=lambda x: x.get("price") or 9999)[:3]:
                            self.upsert_listing(plant["id"], prod)
                    else:
                        print("  No results")
                except Exception as e:
                    print(f"  Error: {e}")
                time.sleep(2)
            browser.close()

    def _search(self, page, plant):
        queries = [plant.get("common_name_sv",""), plant.get("latin_name","")]
        for query in queries:
            if not query: continue
            results = self._search_query(page, query)
            if results: return results
            time.sleep(1)
        return []

    def _search_query(self, page, query):
        try:
            url = f"https://www.wexthuset.com/search?q={requests.utils.quote(query)}"
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            products = []
            cards = page.query_selector_all("li.product, .product-item, [class*='ProductCard'], [class*='product-card']")
            
            for card in cards[:5]:
                try:
                    name = card.query_selector("h2, h3, [class*='name'], [class*='title']")
                    price = card.query_selector("[class*='price'], .price")
                    link = card.query_selector("a")
                    
                    name_text = name.inner_text().strip() if name else ""
                    price_text = price.inner_text().strip() if price else ""
                    href = link.get_attribute("href") if link else ""
                    
                    price_val = self.parse_price(price_text)
                    if href and not href.startswith("http"):
                        href = self.retailer_url + href
                    
                    if name_text and price_val and href:
                        products.append({"name": name_text, "price": price_val, "url": href, "in_stock": True})
                except:
                    continue
            
            # Also try JSON data in page source
            if not products:
                content = page.content()
                prices = re.findall(r'"price":\s*"?(\d+\.?\d*)"?', content)
                names = re.findall(r'"name":\s*"([^"]{3,60})"', content)
                urls = re.findall(r'"url":\s*"(https://www\.wexthuset\.com/[^"]+)"', content)
                for i in range(min(len(prices), len(names), len(urls), 3)):
                    try:
                        products.append({"name": names[i], "price": float(prices[i]), "url": urls[i], "in_stock": True})
                    except:
                        continue

            return products
        except Exception as e:
            print(f"  Search error: {e}")
            return []

if __name__ == "__main__":
    WexthusetScraper().run()
