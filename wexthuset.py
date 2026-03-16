import os, time, re, requests, json
from base_scraper import BaseScraper

class WexthusetScraper(BaseScraper):
    retailer_slug = "wexthuset"
    retailer_name = "Wexthuset"
    retailer_url = "https://www.wexthuset.com"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*",
        "Accept-Language": "sv-SE,sv;q=0.9",
        "Referer": "https://www.wexthuset.com/",
    }

    def search(self, plant):
        results = []
        for query in [plant.get("common_name_sv",""), plant.get("latin_name","")]:
            if not query: continue
            found = self._search_api(query)
            if found:
                results.extend(found)
                break
            time.sleep(1)
        return results

    def _search_api(self, query):
        # Try Wexthuset's search suggestions API
        endpoints = [
            f"https://www.wexthuset.com/api/search?q={requests.utils.quote(query)}&limit=5",
            f"https://www.wexthuset.com/search/suggest?q={requests.utils.quote(query)}",
            f"https://www.wexthuset.com/apps/search/predict?q={requests.utils.quote(query)}&resources[type]=product&resources[limit]=5",
        ]
        
        for url in endpoints:
            try:
                r = requests.get(url, headers=self.HEADERS, timeout=10)
                print(f"  API {url[-50:]} → {r.status_code} ({len(r.text)} chars)")
                if r.status_code == 200 and len(r.text) > 100:
                    return self._parse_response(r, query)
            except Exception as e:
                print(f"  API error: {e}")
                continue
        
        # Fallback: scrape search page with requests
        return self._scrape_search_page(query)

    def _scrape_search_page(self, query):
        try:
            url = f"https://www.wexthuset.com/search?q={requests.utils.quote(query)}&type=product"
            r = requests.get(url, headers=self.HEADERS, timeout=15)
            print(f"  Page scrape → {r.status_code} ({len(r.text)} chars)")
            
            if r.status_code != 200:
                return []

            content = r.text
            
            # Look for product JSON in page
            products = []
            
            # Try to find product data in script tags
            json_pattern = re.findall(r'\"price\":\s*(\d+\.?\d*)', content)
            name_pattern = re.findall(r'\"title\":\s*\"([^\"]{3,80})\"', content)
            url_pattern = re.findall(r'\"url\":\s*\"(/[^\"]+)\"', content)
            handle_pattern = re.findall(r'\"handle\":\s*\"([^\"]+)\"', content)
            
            print(f"  Found: {len(json_pattern)} prices, {len(name_pattern)} names, {len(handle_pattern)} handles")
            
            # Try matching prices with handles
            for i in range(min(len(json_pattern), len(handle_pattern), 5)):
                try:
                    price = float(json_pattern[i]) / 100 if float(json_pattern[i]) > 1000 else float(json_pattern[i])
                    handle = handle_pattern[i]
                    name = name_pattern[i] if i < len(name_pattern) else handle
                    product_url = f"https://www.wexthuset.com/products/{handle}"
                    
                    if price > 0 and price < 5000:
                        products.append({
                            "name": name,
                            "price": price,
                            "url": product_url,
                            "in_stock": True
                        })
                except:
                    continue
            
            return products
            
        except Exception as e:
            print(f"  Scrape error: {e}")
            return []

    def _parse_response(self, r, query):
        try:
            data = r.json()
            products = []
            
            # Handle different API response formats
            items = data.get("products", data.get("results", data.get("resources", {}).get("results", {}).get("products", [])))
            
            for item in items[:5]:
                price = item.get("price", item.get("variants", [{}])[0].get("price", 0))
                if isinstance(price, str):
                    price = self.parse_price(price)
                elif isinstance(price, int) and price > 10000:
                    price = price / 100
                    
                url = item.get("url", item.get("handle", ""))
                if url and not url.startswith("http"):
                    url = f"https://www.wexthuset.com{url}"
                
                name = item.get("title", item.get("name", ""))
                
                if name and price and url:
                    products.append({"name": name, "price": float(price), "url": url, "in_stock": True})
            
            return products
        except:
            return []

if __name__ == "__main__":
    WexthusetScraper().run()
