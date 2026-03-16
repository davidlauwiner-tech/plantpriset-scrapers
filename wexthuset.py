import os, time, re, requests, gzip
from bs4 import BeautifulSoup
from base_scraper import BaseScraper

class WexthusetScraper(BaseScraper):
    retailer_slug = "wexthuset"
    retailer_name = "Wexthuset"
    retailer_url = "https://www.wexthuset.com"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
    }

    def get_product_catalogue(self):
        """Fetch all product URLs from sitemap."""
        print("Building product catalogue from sitemap...")
        products = {}  # name -> {url, price}
        
        try:
            # Try sitemap index
            r = requests.get("https://www.wexthuset.com/sitemap.xml", headers=self.HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "xml")
            
            # Find product sitemaps
            sitemaps = [loc.text for loc in soup.find_all("loc") if "product" in loc.text.lower()]
            print(f"Found {len(sitemaps)} product sitemaps")
            
            for sitemap_url in sitemaps[:3]:  # Limit to first 3 sitemaps
                try:
                    sr = requests.get(sitemap_url, headers=self.HEADERS, timeout=15)
                    if sr.content[:2] == b'\x1f\x8b':  # gzip
                        content = gzip.decompress(sr.content).decode('utf-8')
                    else:
                        content = sr.text
                    
                    ssoup = BeautifulSoup(content, "xml")
                    urls = [loc.text for loc in ssoup.find_all("loc")]
                    print(f"  {sitemap_url}: {len(urls)} URLs")
                    
                    for url in urls:
                        # Extract product name from URL
                        slug = url.rstrip('/').split('/')[-1]
                        name = slug.replace('-', ' ').title()
                        products[slug] = {"url": url, "name": name}
                    
                    time.sleep(1)
                except Exception as e:
                    print(f"  Sitemap error: {e}")
                    continue
        except Exception as e:
            print(f"Sitemap fetch error: {e}")
        
        print(f"Total products in catalogue: {len(products)}")
        return products

    def search(self, plant):
        """Match plant against product catalogue."""
        results = []
        queries = [
            plant.get("common_name_sv", "").lower(),
            plant.get("latin_name", "").lower().split()[0] if plant.get("latin_name") else "",
        ]
        
        for slug, product in self._catalogue.items():
            for query in queries:
                if not query: continue
                if query in slug or query in product["name"].lower():
                    # Fetch price from product page
                    price = self._get_price(product["url"])
                    if price:
                        results.append({
                            "name": product["name"],
                            "price": price,
                            "url": product["url"],
                            "in_stock": True
                        })
                    break
            if results:
                break
        
        return results[:3]

    def _get_price(self, url):
        """Fetch price from a product page."""
        try:
            r = requests.get(url, headers=self.HEADERS, timeout=10)
            if r.status_code != 200:
                return None
            
            # Look for price in JSON-LD
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Try JSON-LD structured data
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, list): data = data[0]
                    price = data.get("offers", {}).get("price") or data.get("price")
                    if price: return float(str(price).replace(",", "."))
                except: continue
            
            # Try meta tags
            price_meta = soup.find("meta", {"property": "product:price:amount"}) or \
                        soup.find("meta", {"itemprop": "price"})
            if price_meta:
                return self.parse_price(price_meta.get("content", ""))
            
            # Try common price selectors
            for selector in [".price", "[class*='price']", "[data-price]"]:
                el = soup.select_one(selector)
                if el:
                    price = self.parse_price(el.get_text())
                    if price and 10 < price < 10000:
                        return price
            
            return None
        except Exception as e:
            return None

    def run(self):
        print(f"=== {self.retailer_name} Scraper ===")
        self._catalogue = self.get_product_catalogue()
        
        if not self._catalogue:
            print("No catalogue built — falling back to search")
            self._catalogue = {}
        
        plants = self.get_all_plants()
        stats = {"searched": 0, "found": 0, "errors": 0}

        for i, plant in enumerate(plants):
            name = plant.get("common_name_sv") or plant.get("slug")
            print(f"\n[{i+1}/{len(plants)}] {name}")
            stats["searched"] += 1
            try:
                products = self.search(plant)
                if products:
                    for p in sorted(products, key=lambda x: x.get("price") or 9999)[:3]:
                        self.upsert_listing(plant["id"], p)
                        stats["found"] += 1
                else:
                    print("  No results")
            except Exception as e:
                print(f"  Error: {e}")
                stats["errors"] += 1
            time.sleep(1)

        print(f"\n=== Done === Searched:{stats['searched']} Found:{stats['found']} Errors:{stats['errors']}")

if __name__ == "__main__":
    WexthusetScraper().run()
