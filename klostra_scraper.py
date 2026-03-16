import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.klostra.se"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

CATEGORY_URLS = ["/froer", "/tradgardstillbehor"]

def scrape_category(session, path):
    products = []
    page = 1
    while True:
        url = f"{BASE_URL}{path}" + (f"?p={page}" if page > 1 else "")
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200: break
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("li.product-item")
            if not cards: break
            before = len(products)
            for card in cards:
                p = {"retailer": "klostra", "category_url": path}
                name_el = card.select_one(".product-item-link")
                if name_el:
                    p["name"] = name_el.get_text(strip=True).replace("Blomfröer","").replace("Grönsaksfröer","").strip()
                    href = name_el.get("href", "")
                    if href: p["product_url"] = href
                price_el = card.select_one("[data-price-amount]")
                if price_el:
                    try: p["price_sek"] = float(price_el["data-price-amount"])
                    except: pass
                img = card.select_one("img.product-image-photo")
                if img: p["image_url"] = img.get("src", "")
                stock_el = card.select_one(".product-availability-info")
                if stock_el:
                    p["in_stock"] = "lager" in stock_el.get_text().lower()
                    p["stock_info"] = stock_el.get_text(strip=True)
                props_el = card.select_one(".product-properties")
                if props_el: p["extra_info"] = props_el.get_text(strip=True)
                p["scraped_at"] = datetime.utcnow().isoformat()
                if p.get("name") and p.get("price_sek"):
                    products.append(p)
            if len(products) == before: break
            next_link = soup.select_one(f'a[href*="p={page+1}"]')
            if next_link:
                page += 1
                time.sleep(1.5)
            else: break
        except Exception as e:
            print(f"    ERROR: {e}")
            break
    return products, page

def main():
    print("=" * 55)
    print("PLANTPRISET — Klostra Scraper")
    print("=" * 55)
    session = requests.Session()
    session.headers.update(HEADERS)
    all_products = []
    for i, cat in enumerate(CATEGORY_URLS, 1):
        products, pages = scrape_category(session, cat)
        page_info = f" ({pages} pages)" if pages > 1 else ""
        print(f"[{i}/{len(CATEGORY_URLS)}] {cat} → {len(products)} products{page_info}")
        all_products.extend(products)
        time.sleep(1.5)
    seen = set()
    unique = [p for p in all_products if not (p.get("product_url","") in seen or seen.add(p.get("product_url","")))]
    with open("klostra_products.json", "w", encoding="utf-8") as f:
        json.dump({"retailer":"klostra","scraped_at":datetime.utcnow().isoformat(),"total_products":len(unique),"products":unique}, f, ensure_ascii=False, indent=2)
    print(f"\nDONE! {len(unique)} unique products → klostra_products.json")
    prices = [p["price_sek"] for p in unique if p.get("price_sek")]
    if prices: print(f"Prices: {min(prices):.0f} – {max(prices):.0f} kr (avg {sum(prices)/len(prices):.0f} kr)")

if __name__ == "__main__":
    main()
